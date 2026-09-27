# History rewrite — 2026-09-27

**What happened.** The repository's Git history was rewritten with `git filter-repo` and
`main` was force-pushed. Every commit hash changed. The pre-rewrite history is retained by the
maintainer as a private bundle outside the repository; it is not published because it contains the
names that were removed.

**Why.** Early versions of `REPLICATION.md` (from the v3 report onward) printed three flagged
package names from a pre-campaign gpt-oss run as examples of standard-library confusion and of a
plausible sibling of a real package. All three were still unregistered on PyPI on 2026-09-27
(absent from both the 2024-01-10 and 2026-08-12 snapshots). The repository's release policy is
not to publish candidate unregistered names, because they are slopsquatting targets. The names
were redacted from the current documents in the (pre-rewrite) commit `74ca050`, but every earlier
revision still contained them. This rewrite removes them from history as well.

**What changed.**

- In every revision of `REPLICATION.md`, the three backticked names were replaced by
  `` `[redacted-stdlib-module-name]` `` (twice) and `` `[redacted-nonexistent-sibling-name]` ``.
  The rules matched only the backticked, lower-case tokens, so no prompt dataset, registry
  snapshot, or mitigation data file was touched (verified across all revisions).
- The single historical `REPLICATION.pdf` blob that contained the names (added in the pre-rewrite
  commit `eac1434`) was stripped from every commit. The redacted PDF committed on 2026-09-27
  remains.
- A local, never-pushed `refs/codex/turn-diffs/checkpoints/...` ref, which pointed at a working-tree
  snapshot holding the old PDF, was deleted so that garbage collection could remove the blob.
- Two other flagged names that appear in `REPLICATION.md`, `AUDIT_RESPONSE.md`, and
  `codex-experiment.md` were left in place: both are registered on PyPI today and cannot be
  squatted.
- No other file content changed. Commit messages that cited old hashes were updated by
  `filter-repo`.

**What this does not do.** A force-push does not immediately purge old commits from the hosting
provider; commits fetched by hash may remain reachable on GitHub until its garbage collection runs
(GitHub support can purge them on request), and any clone or fork made before 2026-09-27 still
contains the old history. Anyone with such a clone should re-clone rather than pull.

**Provenance consequences.** The retrospective provenance stamp
(`Experiments/PROVENANCE_STAMP_2026-08-26.md`), the review amendments
(`Experiments/FABLE_REVIEW_AMENDMENTS_2026-08-26.md`), the paper, and its build scripts cite
pre-rewrite commit ids. Those ids now map as follows. File-content hashes in the stamp are
unaffected: the rewrite changed no file other than `REPLICATION.md` and `REPLICATION.pdf`.

| Pre-rewrite commit | Post-rewrite commit | Note |
|---|---|---|
| `3c021c0` | `bc944b5` | first revision that printed the names (v2/v3 replication report) |
| `8daff30` | `4f67e9e` | Campaign 4 preregistration freeze |
| `d6cb11d` | `8273f0a` | Campaign 4 final corrected results |
| `08c6933` | `cd1ba10` | REPLICATION v4, Part II |
| `1d6f052` | `aaf533b` | Churilov comparison added |
| `eac1434` | `a212e05` | six-cell bridge artifact; parent commit named in the provenance stamp |
| `8bcde48` | `2850472` | cloud experiment results and provenance locked; tag `experiment-kimi-cloud-2026-08-26` |
| `0be12b1` | `c03aad7` | post-analysis review corrections |
| `226f918` | `2ebb230` | findings deck |
| `4a9a6d4` | `47b1b6d` | manuscript draft |
| `75f507b` | `5a542d3` | manuscript readability pass |
| `74ca050` | `5b6da1f` | redaction of the current documents and ethics-section caveats |

Full map (`old new`), as written by `filter-repo`:

```
08c6933787e90f65bd92139a4064333a668205ed cd1ba108f1abbf4ce625f750a87f7438e6d107d6
0be12b1a2ec8e4f844eaa7870f1f0a3bd6a1d6b8 c03aad72f3e6f2a012f777f98c7da9e388ea11b2
131b498439da14d3011cbd0973d0d6ecedb0b4b8 9bb97a85fbb0e520d119b492d715287bc3df3e5e
134ac8c9fafd1f756da696edbaff81b97dc68731 6e1e151a53d224a167f7d3817b32517c58e3ac98
147e10caf1d37e24ecf88857bdf083cd5b2add54 4925035f68e76e0d0f25fa9f78d098c46d005645
17d55ea697531c880e7679ee09423bda32ed44d7 7c1a3a22d5145f6937fc0bd3df195212461b583e
19275db7c195da7fc05d203d01e6135e2be2757a 4e26c9ca1c6676cb72fe27523c80c99922f89e47
1d6f052e63a14c6325c6f5cba0f3070321d87f7f aaf533bf3601333961a08327131b0049fd696b6a
1e28c5d00725d574fee707815dc0927676150a77 0ef258dde929f2c64b79539418da0d001c7bdf29
21f6afab8f5e8b0fa68a3f9dac9335e4609924cc d6a597d400f34b93eacbc4db98021e8ad6594cf2
226f918dd0bdd10e873eef9fa333d4cd7243c831 2ebb2303f72aeac78411937a6d0f11b7f1d03317
270ed8879248c308631bea7161cae220e41c064d ab708292dab0258d7f02faf457e0920c2c07bbed
2c6d44e9ec2ce2b9b664e4efe07003eaac9b5091 1855aced29fb8d21e1c7f57c514c4399be984df5
3c021c0338f40d7d3b4255bfb6309b09834c5d2a bc944b59da8a5a41f652459121e1eb5cf5530898
3ce8536bfd032a5deb718eca6f361b46bdda3927 fdc28f50a6d53563e19452f11fc89fb7d7c956ea
3d9be868016ac11d0a733d095a83db24e5208704 8e5fb12f8ab37b8a05a6fd24c7ea1c329b4d2c2f
4a9a6d428c8a71cb00fa84f0d2d919264437f076 47b1b6d87289aa31f351750595c1c5f2351056d5
4b344743b7c5ecd7d5a1008347aa006589eeb069 5115f2f0c8e1947a232338faf10a6e739adfd90c
56b9ccc5dbc5fe74131fd6f1c83fe6868ad950ef fa02b694e836224e7ce73da831c36245a4564207
57d7982b05cfe7f07a48cba2567c6077b6034a70 e61776fb8da2e0bc8f8ff86e0447e21e8da00414
74ca0502c48c18e95409a94573a1402d21afad59 5b6da1fff0ef8a53ed15c24dc6630a1171df8892
75f507bd32dc8b218e9382814c13b4aba0e559cf 5a542d36c8e69fc93b2944893acfd4f265d6531d
861921d4bb61722bcedf8773874565924950377e 71b8209ff073fa712f38d78bb293a0f5cbd5ec4a
8bcde486a3dbd1d1bffe45410465748bfc173f3e 2850472ae82c2e97516a083100bcd6d9b1771082
8daff3025627fc70241e7a91587fd5c6146c1224 4f67e9eeb71fbee64e212f6fbbf8df755748782d
960289569883305ee130b2e81ec9d6a39597b7eb f63df1cb1ae68781f6ed7154036e54c89784dc9f
beaff792f8d94d3913e5b957e75cc881744d8cc5 f77c39aec3f568ef81d7a18392e01afddf569a79
d4011de94e12a71f813bfbfc4b908a62bc621152 504e8324d497cffa8c0e1a427b870042ae605428
d441124ee2e457b4fdb518c8411610b84f25fd37 b4398c515d92a3594d920f9e5950edf5f547ea33
d6cb11d043756c3445b1f4b865f487b5f0453729 8273f0a26612a067f89bddb043f10f3bb2327724
eac1434964427ad114b548e5327e54301e619ada a212e0589db44177ad3b74b278caa2d0464fe04e
edc0131b47b27589d8962f32044a2da6e2079c72 543244906fbab4ee2166d6c9926a5fdfa1fec345
f9ddf10641864dfce4ab0b7c6e04cbd9f43af431 c6d83f09a4a8d14052a6f9fe72a7574356d42a78
```
