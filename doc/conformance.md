# Conformance

depo's content addresses are part of a scheme shared with sibling projects.
This document is depo's normative statement of that scheme and of how an
implementation is proven to conform. It mirrors the ratified cross-project
contract; where implementation and this document conflict, this document
wins. The scheme itself (how depo derives and stores codes) is described in
[shortcodes](./shortcodes.md); this document covers what must be proven and
where each expected value comes from.

## The scheme

Addresses are unkeyed blake3, sliced on a 40-bit ladder, encoded low-pad
bitstream Crockford Base32. Unkeyed is load-bearing, not a default: keying
would make identical content produce different addresses, which defeats
content-addressing by breaking cross-project dedup and recompute from
content. Enumeration privacy, if ever wanted, belongs at the access layer
that governs who may resolve an address, never in the hash.

The 40-bit ladder is the least common multiple of the 8-bit byte and the
5-bit Crockford symbol. Exact prefixing (a short code being a true prefix
of a longer one) holds only when the short length is a multiple of 40 bits.
Power-of-two widths (64, 128, 256) are off-ladder and break prefixing; all
canonical and prefix lengths are multiples of 40 bits. Width is therefore
self-evident from code length and is never stored: exact for canonical
codes, and within 4 bits for an arbitrary foreign code, which prefix
resolution tolerates since depo resolves on prefixes, not exact digests.

## The governing rule

Expected outputs are never agreed by consensus, because consensus only
makes every implementation wrong together. Every expected value traces to a
certifier none of the projects authored. What follows is mostly a record of
where each value comes from and what independent thing certifies it.

## Oracle pins

blake3 output is not hand-derivable, so the only trusted source is the
official BLAKE3 reference test vectors at a pinned commit (BLAKE3-team/BLAKE3,
test_vectors/test_vectors.json, tag 1.8.5, commit 93a431c78a52..., SHA-256
dcb91ea8...). depo never computes a blake3 value to certify against; it lifts
hex from the pinned file. The commit pins provenance; the file hash lets a
regenerator confirm the exact bytes before generating, so a bad fetch fails
loud. depo ratifies these pins by independently fetching the file and
reproducing the hash, not by accepting the recorded value.

There is no Crockford reference-vector file, so encoding is sourced four
ways, each independent along a different axis. The governing draft
(draft-crockford-davis-base32-for-humans-01) publishes short text rows
(f to CR, foo to CSQPY, foobar to CSQPYRK1E8, test to EHJQ6X0) that are the
only externally-authored Crockford vectors; they are transcribed by
hand-decoding bits, never blind paste, and being low-pad byte-stream they
anchor bit-mechanics as well as the alphabet. Beyond those, two encoders of
independent code lineage are compared live every run: a from-scratch
bit-window encoder (the shipped implementation) and the standard library's
RFC 4648 base32 plus a separately-certified alphabet map (the verifier). A
foreign-runtime RFC 4648 encoder, padding stripped and alphabet translated,
reduces the shared-substrate residual over arbitrary inputs. Where the draft
diverges from crockford.com, the draft wins.

## Alphabet independence

The encoder lineages must not share an alphabet literal, or a shared typo
passes all of them. The implementation carries the literal 32-character
alphabet (0-9, then A-Z excluding I, L, O, U). The verifier does not assert
a literal; it constructs the alphabet from rules (digits 0-9 at positions
0-9, then A-Z skipping exactly I, L, O, U, length 32, all unique, monotonic,
skip transitions H to J, K to M, N to P, T to V) and asserts the
implementation's literal matches. The draft text rows decode to fixed
positions neither definition authored. A literal typo, a construction bug,
and a wrong model fail differently, so they do not fail identically at once.

## Assertion classes

The hasher is proven three ways. Hard-shape vectors: reference hex at chunk
boundaries (1023, 1024, 1025) and multi-chunk sizes, matched by the shipped
hasher reading the frozen file, never calling its own hasher for the
expected value. Digest XOF prefix: one reference extended output sliced at a
short and a long length, asserting the short is a true byte-prefix of the
long, with the long length crossing blake3's 64-byte output-block boundary,
since within one block a broken XOF looks correct. Runtime property:
separately, the shipped build's short output byte-prefixes its long output,
proving the running binary has the property, not just the frozen values.

The encoder is proven over a bounded domain rather than merely sampled.
Bit-mechanics are a stateless streaming map, so every input up to a small
length (covering all residue and window-transition cases) is encoded and
cross-lineage compared: proof over that range, not sampling. Length and pad
across residues use periodic patterns: byte input gives bit-residue 3n mod
5, so lengths 10 through 14 bytes cover all five pad cases, each holding two
full output periods so a streaming-state bug shows at the repeat. 0xAA is
primary (alternating symbols catch ordering bugs), 0xFF a tail-confirmer,
0x00 for length only. Any period feeding an arithmetic cross-check is
hand-derived from the bit stream, never lifted from the encoder's own
output; the period-times-N-plus-tail expression is a localizer against the
full literal encode, never the source value, which closes correlated human
tail-error. Property fuzz with shrinking asserts alphabet closure, the
length invariant, decode(encode(x)) equals x, and the prefix and length
metamorphic laws, seeded from a good source per run so coverage compounds,
with the seed and the minimal failing input in every failure message so a
failure reproduces and graduates into the frozen file.

Composition joins the two: reference input, pinned reference hex, encoder
lineages agree, address. Reference inputs only, so every digest stays
externally certified. No external expected address exists or is needed: the
composition is trustworthy on the reference inputs because those digests are
externally certified and the encoder agrees across lineages and substrates
on them, with exhaustive-small and property fuzz extending confidence toward
domain-completeness. The ladder prefix class slices at two ladder-aligned
lengths crossing the 64-byte boundary and asserts both the digest-byte and
encoded-string prefixes hold. The ladder guard asserts prefixing holds
on-ladder and breaks off-ladder, so widening to a non-40-bit width fails red
rather than silently; width is enforced at the XOF cut.

## Frozen versus live

The frozen file of committed values is authoritative for daily reference and
is falsifiable. On any frozen-versus-live disagreement the build fails hard;
neither side silently wins. Investigation re-derives from the external
sources, never by trusting a runtime artifact. A frozen value is never
silently edited; a correction is a re-derivation with bumped provenance and
is auditable. This gives one authoritative reference without treating the
file as infallible.

## Decoder contract

The strict core rejects anything outside the canonical alphabet, including
U, O, I, L, and depo ships the strict core. U is not an ambiguity coercion
in the class of O, I, L: those are excluded for visual ambiguity and are
invalid in both the data alphabet and the checksum set, so coercing them is
unconditionally safe, whereas U was dropped to reach 32 characters (a vowel,
to avoid forming words) and then reserved with four non-alphanumerics as the
optional mod-37 checksum symbols, so U is meaningful (value 36) in a
checksummed string. A later lenient wrapper, per-project and opt-in with
caller-declared flags, coerces O to 0 and I and L to 1 unconditionally, but
coerces U to V only when both lenience is on and the input is declared
non-checksum; U is never coerced by inference. Lenient decode never emits a
stored value; it funnels human input toward the one canonical form, so it
cannot cause dialect drift. depo intends to ship the lenient wrapper as its
default lookup path once available, since human code entry needs it; details
of depo's canonicalization are in [shortcodes](./shortcodes.md).

## Wrong-address resolution

Hash bugs are effectively all-or-nothing: a broken hasher fails the
reference vectors on the first run, so a silently-wrong hasher persisting is
not realistic. If a wrong but deterministic address was stored before
detection it is still internally consistent, every reference reaching the
right content, mislabeled only against canonical. The immediate stopgap
flags the address as known non-canonical, keeps presenting it consistently
internally, and withholds it from canonical interop so no peer mis-dedups.
Full resolution, once the mutable-link layer exists, offers the owner a
choice to rehash (correcting the code, aliasing old to new so circulated
references survive) or keep the stable circulated code, since rehashing is a
mutation of an otherwise immutable address.

## Honest scope

This is not bulletproof. Every layer is certified by something its own logic
did not author: digest by the reference file, bit-mechanics by exhaustive
small-domain plus cross-lineage and cross-substrate compare, alphabet by
construction plus draft rows, length and pad by periodic vectors against
literal encodes, roundtrip and metamorphic laws by directed fuzz. Residual
assumptions remain: the same-substrate compare shares a runtime (reduced but
not removed by the foreign-runtime differential), the governing draft is
assumed correct, coverage is finite though exhaustive over the small domain,
and the pinned commits are trusted. The accurate claim is: correct relative
to the reference file, the draft, and the runtimes, up to the coverage of
the sampled and exhaustive classes. The contract is final when the
independent per-repo derivations converge, and reopens if a better proof or
an error is found.