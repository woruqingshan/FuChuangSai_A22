# EchoMimicV3 Flash-Pro renderer

The avatar service supports `AVATAR_RENDERER_BACKEND=echomimic_v3` while retaining
`soulxflashhead` as a rollback backend.

## Server layout

```text
/root/autodl-tmp/a22/code/echomimic_v3
/root/autodl-tmp/a22/.uv_envs/echomimic-v3
/root/autodl-tmp/a22/models/echomimic_v3_flash
```

Bootstrap the isolated environment with:

```bash
./scripts/remote/bootstrap_echomimic_v3.sh
```

The renderer consumes the generated WAV, the selected reference image, and a
prompt derived from `emotion_style`, `facial_expression`, and `head_motion`.
Each turn gets a separate output directory to avoid concurrent filename clashes.

## Reference image requirement

Use a front-facing, waist-up image with both arms and free space around the hands
for gesture evaluation. Existing close-up portraits can validate facial motion but
cannot produce reliable visible hand gestures.

## Rollback

Set the following before starting the remote stack:

```bash
export AVATAR_RENDERER_BACKEND=soulxflashhead
```

No SoulX model, environment, bridge, or configuration is removed by this change.
