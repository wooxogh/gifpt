# Speculative Decoding for Faster LLM Inference

## Problem

Autoregressive LLM decoding is slow because each token must be generated one at a time — every step is a full forward pass through the (large) target model `M_p`. Throughput is bottlenecked by sequential token generation, not raw FLOPs.

## Key insight

Most generated tokens are "easy" — a much smaller, much faster draft model `M_q` can predict them correctly. We can:
1. Have the draft model speculate the next K tokens cheaply.
2. Run the target model **once** in parallel over all K speculated tokens to verify them.
3. Accept the longest correctly-predicted prefix; reject the first wrong one and replace it with the target model's distribution.

If the draft is correct most of the time, we generate ≈K tokens per single target forward pass — a multiplicative speedup with no quality loss.

## Algorithm (one decoding step)

Inputs: prompt context `x_1..x_t`, target model `M_p`, draft model `M_q`, lookahead `K` (e.g., 5).

1. **Draft**: Use `M_q` to autoregressively sample `K` candidate tokens `x_{t+1}, ..., x_{t+K}`, recording the draft probabilities `q(x_i | ...)` at each step.
2. **Verify (parallel)**: Run `M_p` once on the extended sequence `x_1..x_{t+K}`. This yields target probabilities `p(x_i | ...)` for every position simultaneously, thanks to the causal attention mask.
3. **Accept/reject**: Walk through positions `i = t+1 ... t+K` in order. At each position:
   - Sample `r ~ Uniform(0, 1)`.
   - Accept if `r < p(x_i) / q(x_i)`. Otherwise reject.
   - On the first rejection at position `j`, resample `x_j` from the corrected distribution `(p - q)_+ / Z` and stop.
4. **Output**: Append accepted tokens to the running output, plus the corrected token if any rejection happened. If all K were accepted, append one bonus token sampled from `M_p`'s distribution at position `t+K+1` (free, since we already ran `M_p` there).

## Properties

- **Lossless**: Output distribution is provably identical to `M_p` decoding. The accept/reject rule is rejection sampling, not approximation.
- **Adaptive**: When draft and target agree often (easy tokens), most candidates are accepted → near `K`× speedup. On hard tokens, the first one fails fast → minimal waste.
- **Hardware-friendly**: The K parallel target evaluations cost roughly the same wall-clock as one target evaluation, because GPU utilization on a sequence of K is well below saturation for typical K.

## Visual story for animation

The most visually striking moments are:
1. **The race**: small draft model fires off K tokens fast, large target model lumbers along.
2. **The verification**: target model evaluates all K positions in *one* pass — show the parallelism explicitly.
3. **Accept/reject walk**: tokens get colored green (accepted) or red (rejected) as the rule is applied left-to-right.
4. **The payoff**: counter shows "5 tokens generated, 1 target forward pass" — speedup is the punchline.
