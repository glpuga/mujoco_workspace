"""Focused checks for marble configuration, spawning and backend selection."""

import contextlib
import io
import os
import unittest
from unittest import mock

import main as marbles
import mujoco
import numpy as np


class MarbleSimulationTests(unittest.TestCase):
    def test_command_line_settings(self) -> None:
        """Accept explicit settings and keep CPU physics as the default."""
        settings = marbles.parse_arguments(
            ["--drop-interval", "0.1", "--marble-count", "2", "--warp"]
        )
        self.assertEqual(settings.drop_interval, 0.1)
        self.assertEqual(settings.marble_count, 2)
        self.assertTrue(settings.warp)
        self.assertFalse(marbles.parse_arguments([]).warp)

    def test_invalid_settings(self) -> None:
        """Reject invalid counts and non-finite or non-positive intervals."""
        for option, values in (
            ("--drop-interval", ["0", "-1", "nan", "inf", "not-a-number"]),
            ("--marble-count", ["0", "-1", "1.5", "not-a-number"]),
        ):
            for value in values:
                with self.subTest(option=option, value=value):
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as error:
                            marbles.parse_arguments([option, value])
                    self.assertEqual(error.exception.code, 2)

    def test_pool_size_drop_interval_and_reuse(self) -> None:
        """Respect the selected schedule and reset recycled marbles."""
        model = marbles.build_model(2)
        data = mujoco.MjData(model)
        self.assertEqual(model.njnt, 2)
        self.assertEqual(model.nq, 14)
        first, second = marbles._MARBLES
        marbles.control(model, data, 0.0, drop_interval=0.1)
        self.assertEqual(model.body_gravcomp[first.body_id], 0.0)
        self.assertEqual(model.body_gravcomp[second.body_id], 1.0)
        np.testing.assert_array_equal(
            data.qvel[first.velocity_address : first.velocity_address + 6],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )
        mujoco.mj_step(model, data)
        self.assertLess(data.qvel[first.velocity_address + 2], 0.0)

        marbles.control(model, data, 0.05, drop_interval=0.1)
        self.assertEqual(model.body_gravcomp[second.body_id], 1.0)
        marbles.control(model, data, 0.1, drop_interval=0.1)
        self.assertEqual(model.body_gravcomp[second.body_id], 0.0)
        marbles.control(model, data, 0.2, drop_interval=0.1)
        np.testing.assert_array_equal(
            data.qvel[first.velocity_address : first.velocity_address + 6],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )

        # A newly built pool must start its own drop schedule at the first marble.
        rebuilt_model = marbles.build_model(3)
        rebuilt_data = mujoco.MjData(rebuilt_model)
        self.assertEqual(rebuilt_model.njnt, 3)
        marbles.control(rebuilt_model, rebuilt_data, 0.0, drop_interval=0.1)
        self.assertEqual(rebuilt_model.body_gravcomp[marbles._MARBLES[0].body_id], 0.0)

    def check_viewer_loop(self, use_warp: bool) -> None:
        """Exercise actual physics while substituting only the viewer window."""
        arguments = ["main.py", "--marble-count", "2", "--drop-interval", "0.02"]
        if use_warp:
            arguments.append("--warp")
        simulated_viewer = mock.MagicMock()
        simulated_viewer.is_running.side_effect = [True, True, True, False]
        with (
            mock.patch("sys.argv", arguments),
            mock.patch.object(marbles.viewer, "launch_passive") as launch_viewer,
            mock.patch.object(marbles.time, "sleep"),
        ):
            launch_viewer.return_value.__enter__.return_value = simulated_viewer
            marbles.main()
            model, data = launch_viewer.call_args.args
        self.assertEqual(simulated_viewer.sync.call_count, 3)
        self.assertGreater(data.time, 0.04)
        for marble in marbles._MARBLES:
            self.assertEqual(model.body_gravcomp[marble.body_id], 0.0)
            self.assertLess(data.qvel[marble.velocity_address + 2], 0.0)

    def test_cpu_viewer_loop(self) -> None:
        """Run CPU physics through the interactive loop without a display."""
        self.check_viewer_loop(use_warp=False)

    @unittest.skipUnless(
        os.environ.get("TEST_MUJOCO_WARP") == "1", "CUDA test is opt-in"
    )
    def test_warp_viewer_loop(self) -> None:
        """Run actual CUDA physics and transfer the results back to the viewer."""
        self.check_viewer_loop(use_warp=True)

    @unittest.skipUnless(
        os.environ.get("TEST_MUJOCO_WARP") == "1", "CUDA test is opt-in"
    )
    def test_warp_requires_cuda(self) -> None:
        """Reject unavailable CUDA rather than silently switching backends."""
        with (
            mock.patch("sys.argv", ["main.py", "--marble-count", "1", "--warp"]),
            mock.patch("warp.get_cuda_devices", return_value=[]),
        ):
            with self.assertRaisesRegex(RuntimeError, "requires an NVIDIA GPU"):
                marbles.main()


if __name__ == "__main__":
    unittest.main()
