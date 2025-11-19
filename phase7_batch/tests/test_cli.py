from argparse import ArgumentParser, Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from phase7_batch.cli import apply_overrides, build_parser, main
from phase7_batch.models import BatchConfig


class TestParser:
    def test_build_parser_defines_expected_arguments(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--config",
                "custom.yaml",
                "--input-dir",
                "input",
                "--pipeline-json",
                "pipe.json",
                "--max-workers",
                "3",
                "--cpu-threshold",
                "50",
                "--dry-run",
                "--batch-size",
                "4",
                "--phase-timeout",
                "30",
                "--phases",
                "2",
                "4",
            ]
        )

        assert isinstance(parser, ArgumentParser)
        assert args.config == "custom.yaml"
        assert args.dry_run is True
        assert args.max_workers == 3
        assert args.cpu_threshold == 50.0
        assert args.batch_size == 4
        assert args.phases == [2, 4]


class TestApplyOverrides:
    def test_apply_overrides_updates_fields(self, tmp_path):
        config = BatchConfig(
            input_dir=str(tmp_path / "inputs"),
            pipeline_json=str(tmp_path / "pipeline.json"),
        )
        args = Namespace(
            input_dir=str(tmp_path / "override"),
            pipeline_json=str(tmp_path / "override" / "pipeline.json"),
            log_file=str(tmp_path / "logs" / "batch.log"),
            log_level="warning",
            max_workers=8,
            cpu_threshold=60.0,
            throttle_delay=2.0,
            resume=True,
            dry_run=True,
            batch_size=5,
            phases=[3, 4],
            phase_timeout=120,
        )

        updated = apply_overrides(config, args)

        assert updated.input_dir.endswith("override")
        assert updated.pipeline_json.endswith("pipeline.json")
        assert updated.log_file.endswith("batch.log")
        assert updated.log_level == "warning"
        assert updated.max_workers == 8
        assert updated.cpu_threshold == 60.0
        assert updated.throttle_delay == 2.0
        assert updated.batch_size == 5
        assert updated.phases == [3, 4]
        assert updated.dry_run is True

    def test_apply_overrides_handles_resume_flags(self):
        config = BatchConfig()
        args = SimpleNamespace(
            input_dir=None,
            pipeline_json=None,
            log_file=None,
            log_level=None,
            max_workers=None,
            cpu_threshold=None,
            throttle_delay=None,
            resume=False,
            dry_run=False,
            batch_size=None,
            phases=None,
            phase_timeout=None,
        )

        updated = apply_overrides(config, args)

        assert updated.resume is False
        assert updated.dry_run is False


class TestCliMain:
    @patch("phase7_batch.cli.trio.run")
    @patch("phase7_batch.cli.setup_logging")
    @patch("phase7_batch.cli.apply_overrides")
    @patch("phase7_batch.cli.load_config")
    @patch("phase7_batch.cli.build_parser")
    def test_main_invokes_trio_run(
        self,
        mock_build_parser,
        mock_load_config,
        mock_apply_overrides,
        mock_setup_logging,
        mock_trio_run,
    ):
        parser = MagicMock()
        parser.parse_args.return_value = Namespace(config="config.yaml")
        mock_build_parser.return_value = parser
        config = BatchConfig()
        mock_load_config.return_value = config
        mock_apply_overrides.return_value = config
        mock_trio_run.return_value = 0

        exit_code = main()

        assert exit_code == 0
        mock_build_parser.assert_called_once()
        mock_setup_logging.assert_called_once_with(config)
        mock_trio_run.assert_called_once()

    @patch("phase7_batch.cli.trio.run", side_effect=KeyboardInterrupt)
    @patch("phase7_batch.cli.setup_logging")
    @patch("phase7_batch.cli.apply_overrides")
    @patch("phase7_batch.cli.load_config")
    @patch("phase7_batch.cli.build_parser")
    def test_main_handles_keyboard_interrupt(
        self,
        mock_build_parser,
        mock_load_config,
        mock_apply_overrides,
        mock_setup_logging,
        mock_trio_run,
    ):
        parser = MagicMock()
        parser.parse_args.return_value = Namespace(config="config.yaml")
        mock_build_parser.return_value = parser
        config = BatchConfig()
        mock_load_config.return_value = config
        mock_apply_overrides.return_value = config

        exit_code = main()

        assert exit_code == 130
