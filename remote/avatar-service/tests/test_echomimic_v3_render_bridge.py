import unittest

from services.echomimic_v3_render_bridge import EchoMimicV3RenderBridge


class EchoMimicV3RenderBridgeTest(unittest.TestCase):
    def test_align_video_length_uses_wan_temporal_shape(self) -> None:
        bridge = EchoMimicV3RenderBridge()
        self.assertEqual(bridge.align_video_length(1), 1)
        self.assertEqual(bridge.align_video_length(80), 77)
        self.assertEqual(bridge.align_video_length(81), 81)
        self.assertEqual(bridge.align_video_length(84), 81)


    def test_prompt_combines_emotion_expression_and_motion(self) -> None:
        bridge = EchoMimicV3RenderBridge()
        prompt = bridge.build_prompt(
            emotion_style="supportive",
            facial_expression="gentle_smile",
            head_motion="slow_nod",
            prompt_template="She is {emotion_prompt}, showing {expression_prompt}, with {motion_prompt}.",
        )
        self.assertIn("empathetic", prompt)
        self.assertIn("gentle reassuring smile", prompt)
        self.assertIn("slow reassuring nods", prompt)


    def test_cli_uses_official_flash_arguments(self) -> None:
        bridge = EchoMimicV3RenderBridge()
        request = bridge.build_request(
            session_id="s1", turn_id=2, audio_path="/tmp/a.wav", ref_image_path="/tmp/r.png",
            prompt="A person speaks warmly.", negative_prompt="bad hands", width=768, height=768,
            fps=25, video_length=81, steps=8, guidance_scale=6.0,
            audio_guidance_scale=3.0, seed=43,
        )
        args = bridge.build_cli_args(
            request, python_path="/env/bin/python", infer_script="infer_flash.py",
            config_path="config/config.yaml", model_path="/models/base",
            transformer_path="/models/transformer.safetensors", wav2vec_path="/models/wav2vec",
            output_dir="/outputs/s1/2", gpu_memory_mode="sequential_cpu_offload",
            weight_dtype="bfloat16", teacache_threshold=0.1,
        )
        self.assertEqual(args[:2], ["/env/bin/python", "infer_flash.py"])
        self.assertEqual(args[args.index("--prompt") + 1], "A person speaks warmly.")
        self.assertEqual(args[args.index("--video_length") + 1], "81")
        self.assertEqual(
            args[args.index("--transformer_path") + 1],
            "/models/transformer.safetensors",
        )


if __name__ == "__main__":
    unittest.main()
