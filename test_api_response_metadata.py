import json
import os
import tempfile
import unittest

import api_batch
import llm_api
import run_test_api
import score_kimi_k3_extension


class _Response:
    status_code = 200
    headers = {}

    def json(self):
        return {
            "model": "served-model",
            "message": {"content": "pandas, numpy"},
            "prompt_eval_count": 11,
            "eval_count": 7,
            "done_reason": "length",
        }


class _Session:
    def post(self, *_args, **_kwargs):
        return _Response()


class _BatchClient:
    truncated = 0

    def chat(self, _messages, **kwargs):
        self.assert_metadata_requested = kwargs.get("include_metadata") is True
        return "pandas", {"prompt_tokens": 2, "completion_tokens": 1}, {
            "finish_reason": "stop",
            "truncated": False,
            "served_model": "fake",
            "prompt_tokens": 2,
            "completion_tokens": 1,
        }


class ResponseMetadataTests(unittest.TestCase):
    def _write_k3_validation_fixture(self, directory):
        run = "fixture_k3"
        run_dir = os.path.join(directory, "Tests", run)
        os.makedirs(run_dir)
        phases = {}
        for dataset in score_kimi_k3_extension.campaign.KEYS:
            for suffix in ("code", "packages_1", "packages_2"):
                phase = f"{dataset}_{suffix}"
                output = os.path.join(run_dir, f"{phase}.json")
                with open(output, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps("pandas") + "\n")
                sidecar = output + ".request_metadata.jsonl"
                with open(sidecar, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "index": 0,
                        "finish_reason": "stop",
                        "truncated": False,
                        "served_model": "kimi-k3",
                        "prompt_tokens": 2,
                        "completion_tokens": 1,
                    }) + "\n")
                phases[phase] = {
                    "items": 1,
                    "requested": 1,
                    "resumed": 0,
                    "errors": 0,
                    "truncated_new_requests": 0,
                    "response_metadata_rows": 1,
                }
        manifest = {
            "model_spec": "ollama:kimi-k3:cloud",
            "language": "Python",
            "workers": 2,
            "limit": 1,
            "sample": None,
            "seed": None,
            "sampling_requested": {
                "code_temperature": 0.7,
                "package_temperature": 0.01,
                "top_k": 20,
                "top_p": 0.9,
                "max_code_tokens": 4096,
                "max_package_tokens": 2048,
            },
            "client": {
                "extra_body": {"think": False},
                "request_adjustments": {},
                "cost_tracking": {
                    "input_usd_per_million_tokens": 3.0,
                    "output_usd_per_million_tokens": 15.0,
                    "estimated_cost_usd": 0.000252,
                },
            },
            "token_usage_cumulative": {
                "prompt_tokens": 24,
                "completion_tokens": 12,
                "calls": 12,
            },
            "phases": phases,
        }
        with open(os.path.join(run_dir, "run_manifest.json"), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        return run, run_dir

    def test_client_optional_metadata_preserves_default_shape(self):
        client = llm_api.Client(
            "ollama", "requested-model",
            input_cost_per_million=3,
            output_cost_per_million=15,
            budget_usd=95,
        )
        client._session = _Session()
        default = client.chat([], 7)
        self.assertEqual(default, ("pandas, numpy", {"prompt_tokens": 11,
                                                     "completion_tokens": 7}))
        detailed = client.chat([], 7, include_metadata=True)
        self.assertEqual(detailed[2]["finish_reason"], "length")
        self.assertTrue(detailed[2]["truncated"])
        self.assertEqual(detailed[2]["served_model"], "served-model")
        self.assertAlmostEqual(client.estimated_cost_usd, 2 * (11 * 3 + 7 * 15) / 1_000_000)
        self.assertEqual(client.describe()["cost_tracking"]["budget_usd"], 95)

    def test_budget_requires_prices(self):
        with self.assertRaises(llm_api.ProviderError):
            llm_api.Client("ollama", "requested-model", budget_usd=10)

    def test_restore_accounting_seeds_total_cost_not_new_usage(self):
        client = llm_api.Client(
            "ollama", "requested-model",
            input_cost_per_million=3,
            output_cost_per_million=15,
            budget_usd=95,
        )
        restored = client.restore_accounting([
            {"prompt_tokens": 100, "completion_tokens": 200},
            {"prompt_tokens": 50, "completion_tokens": 25},
        ])
        self.assertEqual(restored, {"prompt_tokens": 150,
                                    "completion_tokens": 225, "calls": 2})
        self.assertEqual(client.usage["calls"], 0)
        self.assertEqual(client.restored_accounting_rows, 2)
        self.assertAlmostEqual(client.estimated_cost_usd,
                               (150 * 3 + 225 * 15) / 1_000_000)

    def test_resume_scanner_deduplicates_partial_and_sidecar(self):
        client = llm_api.Client(
            "ollama", "requested-model",
            input_cost_per_million=3,
            output_cost_per_million=15,
            budget_usd=95,
        )
        with tempfile.TemporaryDirectory() as directory:
            partial = os.path.join(directory, "phase.json.partial")
            sidecar = os.path.join(directory, "phase.json.request_metadata.jsonl")
            with open(partial, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"i": 0, "text": "x", "meta": {
                    "prompt_tokens": 10, "completion_tokens": 20}}) + "\n")
                handle.write(json.dumps({"i": 1, "text": "y", "meta": {
                    "prompt_tokens": 30, "completion_tokens": 40}}) + "\n")
            with open(sidecar, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"index": 0, "prompt_tokens": 10,
                                         "completion_tokens": 20}) + "\n")
            restored = run_test_api.restore_response_accounting(directory, client)
        self.assertEqual(restored, {"prompt_tokens": 40,
                                    "completion_tokens": 60, "calls": 2})

    def test_batch_writes_ordered_metadata_sidecar(self):
        client = _BatchClient()
        with tempfile.TemporaryDirectory() as directory:
            outfile = os.path.join(directory, "responses.json")
            stats = api_batch.run_batch(
                client,
                ["one", "two"],
                lambda item: [{"role": "user", "content": item}],
                outfile,
                max_tokens=10,
            )
            with open(outfile + ".request_metadata.jsonl", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            self.assertTrue(client.assert_metadata_requested)
            self.assertEqual([record["index"] for record in records], [0, 1])
            self.assertEqual([record["served_model"] for record in records], ["fake", "fake"])
            self.assertEqual(stats["response_metadata_rows"], 2)
            self.assertEqual(stats["truncated_new_requests"], 0)
            self.assertEqual(stats["truncated_total_rows"], 0)

    def test_batch_resume_reports_complete_phase_truncations(self):
        client = _BatchClient()
        with tempfile.TemporaryDirectory() as directory:
            outfile = os.path.join(directory, "responses.json")
            with open(outfile + ".partial", "w", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "i": 0,
                    "text": "old",
                    "meta": {
                        "finish_reason": "length",
                        "truncated": True,
                        "served_model": "fake",
                        "prompt_tokens": 2,
                        "completion_tokens": 10,
                    },
                }) + "\n")
            stats = api_batch.run_batch(
                client,
                ["one", "two"],
                lambda item: [{"role": "user", "content": item}],
                outfile,
                max_tokens=10,
            )
            self.assertEqual(stats["requested"], 1)
            self.assertEqual(stats["resumed"], 1)
            self.assertEqual(stats["truncated_new_requests"], 0)
            self.assertEqual(stats["truncated_total_rows"], 1)

    def test_k3_gate_accepts_complete_provenance_and_rejects_identity_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            run, run_dir = self._write_k3_validation_fixture(directory)
            previous = os.getcwd()
            try:
                os.chdir(directory)
                result = score_kimi_k3_extension.validate_metadata(run, 1)
                self.assertTrue(result["passed"])
                self.assertEqual(result["totals"]["rows"], 12)
                manifest_path = os.path.join(run_dir, "run_manifest.json")
                with open(manifest_path, encoding="utf-8") as handle:
                    manifest = json.load(handle)
                phase = manifest["phases"]["LLM_Recent_code"]
                phase.update({
                    "requested": 0,
                    "resumed": 1,
                    "truncated_new_requests": 0,
                    "truncated_total_rows": 0,
                })
                with open(manifest_path, "w", encoding="utf-8") as handle:
                    json.dump(manifest, handle)
                self.assertTrue(
                    score_kimi_k3_extension.validate_metadata(run, 1)["passed"]
                )
                del phase["truncated_total_rows"]
                with open(manifest_path, "w", encoding="utf-8") as handle:
                    json.dump(manifest, handle)
                with self.assertRaises(SystemExit):
                    score_kimi_k3_extension.validate_metadata(run, 1)
                phase["truncated_total_rows"] = 0
                with open(manifest_path, "w", encoding="utf-8") as handle:
                    json.dump(manifest, handle)
                path = os.path.join(
                    run_dir, "LLM_Recent_code.json.request_metadata.jsonl"
                )
                with open(path, encoding="utf-8") as handle:
                    record = json.loads(handle.readline())
                record["served_model"] = "unexpected-model"
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                with self.assertRaises(SystemExit):
                    score_kimi_k3_extension.validate_metadata(run, 1)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
