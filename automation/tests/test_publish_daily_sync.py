import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "publish_daily_sync.py"
SPEC = importlib.util.spec_from_file_location("publish_daily_sync", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PublisherBoundaryTest(unittest.TestCase):
  def test_primary_worktree_is_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").mkdir()

      with self.assertRaisesRegex(MODULE.PublishError, "secondary worktree"):
        MODULE.ensure_secondary_worktree(repo_root)

  def test_linked_worktree_is_accepted(self):
    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")

      MODULE.ensure_secondary_worktree(repo_root)

  def test_whitelist_accepts_only_daily_generated_paths(self):
    accepted = MODULE.validate_allowed_paths([
      "1-raw/Joe\u4e3b\u52a8\u6536\u5f55/AI\u8d44\u8baf/2026-08-04__note.md",
      "3-processing/index/intake-baseline.json",
      "3-processing/index/intake-ledger.jsonl",
      "3-processing/wiki/NOW.md",
    ])

    self.assertEqual(len(accepted), 4)
    with self.assertRaisesRegex(MODULE.PublishError, "whitelist rejected"):
      MODULE.validate_allowed_paths(["README.md"])

  def test_rename_status_collects_both_paths(self):
    output = "R  new.md\0old.md\0?? another.md\0"

    self.assertEqual(
      MODULE.parse_porcelain_paths(output),
      ["new.md", "old.md", "another.md"],
    )

  def test_pipeline_result_must_be_explicit(self):
    self.assertEqual(
      MODULE.parse_pipeline_result('{"status":"zero-change","newVersions":0}')["status"],
      "zero-change",
    )
    with self.assertRaises(MODULE.PublishError):
      MODULE.parse_pipeline_result('{"status":"dry-run"}')


class PublisherFlowTest(unittest.IsolatedAsyncioTestCase):
  async def test_dirty_worktree_stops_before_fetch(self):
    calls = []

    async def fake_git_output(repo_root, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      raise AssertionError(args)

    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fake_git_output),
        mock.patch.object(MODULE, "changed_paths", return_value=["README.md"]),
        mock.patch.object(MODULE, "run_command") as pipeline,
      ):
        with self.assertRaisesRegex(MODULE.PublishError, "must be clean"):
          await MODULE.publish(
            repo_root,
            remote="origin",
            branch="main",
            pipeline=MODULE.DEFAULT_PIPELINE,
            lock_path=repo_root / "publisher.lock",
          )

      pipeline.assert_not_called()
      self.assertFalse(any(call[0] == "fetch" for call in calls))

  async def test_zero_change_never_commits_or_pushes(self):
    calls = []

    async def fake_git_output(repo_root, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] == "fetch":
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return "a" * 40
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return "a" * 40
      raise AssertionError(args)

    async def fake_run_command(args, cwd):
      self.assertEqual(args[-1], MODULE.DEFAULT_PIPELINE)
      return MODULE.CommandResult(
        '{"status":"zero-change","newVersions":0,"runDate":"2026-08-04"}',
        "",
      )

    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      lock_path = repo_root / "publisher.lock"
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fake_git_output),
        mock.patch.object(MODULE, "run_command", side_effect=fake_run_command),
        mock.patch.object(MODULE, "changed_paths", side_effect=[[], []]),
      ):
        result = await MODULE.publish(
          repo_root,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=lock_path,
        )

    self.assertEqual(result["status"], "zero-change")
    self.assertFalse(result["commitCreated"])
    self.assertFalse(result["pushed"])
    self.assertFalse(any(call[0] in {"add", "commit", "push"} for call in calls))

  async def test_remote_divergence_stops_before_pipeline(self):
    async def fake_git_output(repo_root, *args):
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] == "fetch":
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return "a" * 40
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return "b" * 40
      if args[0] == "merge-base":
        return "d" * 40
      raise AssertionError(args)

    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fake_git_output),
        mock.patch.object(MODULE, "changed_paths", return_value=[]),
        mock.patch.object(MODULE, "run_command") as pipeline,
      ):
        with self.assertRaisesRegex(MODULE.PublishError, "refusing merge or rebase"):
          await MODULE.publish(
            repo_root,
            remote="origin",
            branch="main",
            pipeline=MODULE.DEFAULT_PIPELINE,
            lock_path=repo_root / "publisher.lock",
          )

      pipeline.assert_not_called()

  async def test_clean_behind_worktree_detaches_at_remote_head(self):
    calls = []
    headReads = iter(["a" * 40, "b" * 40])

    async def fakeGitOutput(repoRoot, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] in {"fetch", "switch"}:
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return next(headReads)
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return "b" * 40
      if args[0] == "merge-base":
        return "a" * 40
      raise AssertionError(args)

    async def fakeRunCommand(args, cwd):
      return MODULE.CommandResult(
        '{"status":"zero-change","newVersions":0,"runDate":"2026-08-04"}',
        "",
      )

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "run_command", side_effect=fakeRunCommand),
        mock.patch.object(MODULE, "changed_paths", side_effect=[[], []]),
      ):
        result = await MODULE.publish(
          repoRoot,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=repoRoot / "publisher.lock",
        )

    self.assertTrue(result["worktreeFastForwarded"])
    self.assertIn(("switch", "--detach", "refs/remotes/origin/main"), calls)

  async def test_remote_advance_after_commit_stops_push(self):
    calls = []
    remote_reads = iter(["a" * 40, "b" * 40])
    raw_path = "1-raw/Joe\u4e3b\u52a8\u6536\u5f55/AI\u8d44\u8baf/2026-08-04__note.md"
    changed = [raw_path, "3-processing/index/intake-ledger.jsonl"]

    async def fake_git_output(repo_root, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] in {"fetch", "add", "commit"}:
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return "a" * 40 if calls.count(("rev-parse", "HEAD")) == 1 else "c" * 40
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return next(remote_reads)
      if args[:3] == ("diff", "--cached", "--name-only"):
        return "\0".join(sorted(changed)) + "\0"
      if args[0] == "push":
        raise AssertionError("push must not run after remote divergence")
      raise AssertionError(args)

    async def fake_run_command(args, cwd):
      for relativePath in changed:
        target = cwd / relativePath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"generated {relativePath}\n", encoding="utf-8")
      return MODULE.CommandResult(
        '{"status":"changed","newVersions":1,"runDate":"2026-08-04"}',
        "",
      )

    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      (repo_root / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fake_git_output),
        mock.patch.object(MODULE, "run_command", side_effect=fake_run_command),
        mock.patch.object(MODULE, "changed_paths", side_effect=[[], changed, changed]),
      ):
        with self.assertRaisesRegex(MODULE.PublishError, "advanced"):
          await MODULE.publish(
            repo_root,
            remote="origin",
            branch="main",
            pipeline=MODULE.DEFAULT_PIPELINE,
            lock_path=repo_root / "publisher.lock",
          )

    self.assertFalse(any(call[0] == "push" for call in calls))

  async def test_changed_pipeline_commits_whitelist_and_fast_forward_pushes(self):
    calls = []
    headReads = iter(["a" * 40, "c" * 40])
    rawPath = "1-raw/Joe\u4e3b\u52a8\u6536\u5f55/AI\u8d44\u8baf/2026-08-04__note.md"
    changed = [rawPath, "3-processing/index/intake-ledger.jsonl"]

    async def fakeGitOutput(repoRoot, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] in {"fetch", "add", "commit", "push"}:
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return next(headReads)
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return "a" * 40
      if args[:3] == ("diff", "--cached", "--name-only"):
        return "\0".join(sorted(changed)) + "\0"
      raise AssertionError(args)

    async def fakeRunCommand(args, cwd):
      for relativePath in changed:
        target = cwd / relativePath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"generated {relativePath}\n", encoding="utf-8")
      return MODULE.CommandResult(
        '{"status":"changed","newVersions":1,"runDate":"2026-08-04"}',
        "",
      )

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "run_command", side_effect=fakeRunCommand),
        mock.patch.object(MODULE, "changed_paths", side_effect=[[], changed, changed]),
      ):
        result = await MODULE.publish(
          repoRoot,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=repoRoot / "publisher.lock",
        )

    self.assertTrue(result["commitCreated"])
    self.assertTrue(result["pushed"])
    self.assertEqual(result["commit"], "c" * 40)
    self.assertIn(("push", "origin", "HEAD:refs/heads/main"), calls)
    self.assertFalse(any("--force" in call for call in calls))


class PublisherRecoveryTest(unittest.IsolatedAsyncioTestCase):
  def writeJournal(
    self,
    path: Path,
    *,
    state: str,
    baseCommit: str,
    paths: list[str] | None = None,
    repoRoot: Path | None = None,
    commit: str | None = None,
  ):
    journal = {
      "schemaVersion": MODULE.JOURNAL_SCHEMA_VERSION,
      "runId": "recovery-run",
      "state": state,
      "remote": "origin",
      "branch": "main",
      "pipeline": MODULE.DEFAULT_PIPELINE,
      "baseCommit": baseCommit,
      "startedAt": "2026-08-04T01:07:00+00:00",
      "worktreeFastForwarded": False,
    }
    if paths is not None:
      assert repoRoot is not None
      journal.update({
        "pipelineResult": {
          "status": "changed",
          "newVersions": 1,
          "runDate": "2026-08-04",
        },
        "paths": paths,
        "pathHashes": MODULE.hash_owned_paths(repoRoot, paths),
      })
    if commit:
      journal["commit"] = commit
    MODULE.atomic_write_json(path, journal)

  async def test_started_journal_resumes_owned_dirty_pipeline(self):
    baseCommit = "a" * 40
    commit = "c" * 40
    rawPath = "1-raw/Joe主动收录/AI资讯/2026-08-04__note.md"
    headReads = iter([baseCommit, commit])
    remoteReads = iter([baseCommit, baseCommit])
    calls = []

    async def fakeGitOutput(repoRoot, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] in {"fetch", "add", "commit", "push"}:
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return next(headReads)
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return next(remoteReads)
      if args[:3] == ("diff", "--cached", "--name-only"):
        return f"{rawPath}\0"
      raise AssertionError(args)

    async def fakeRunCommand(args, cwd):
      (cwd / rawPath).write_text("complete managed content\n", encoding="utf-8")
      return MODULE.CommandResult(
        '{"status":"zero-change","newVersions":0,"runDate":"2026-08-04"}',
        "",
      )

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      target = repoRoot / rawPath
      target.parent.mkdir(parents=True)
      target.write_text("interrupted managed content\n", encoding="utf-8")
      journalPath = repoRoot / "publisher-journal.json"
      self.writeJournal(journalPath, state="started", baseCommit=baseCommit)

      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "run_command", side_effect=fakeRunCommand),
        mock.patch.object(MODULE, "changed_paths", side_effect=[
          [rawPath],
          [rawPath],
          [rawPath],
        ]),
      ):
        result = await MODULE.publish(
          repoRoot,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=repoRoot / "publisher.lock",
          journal_path=journalPath,
        )

      self.assertTrue(result["resumed"])
      self.assertTrue(result["recoveredInterruptedRun"])
      self.assertTrue(result["pushed"])
      self.assertFalse(journalPath.exists())
      self.assertIn(("push", "origin", "HEAD:refs/heads/main"), calls)

  async def test_git_committed_journal_resumes_push_without_pipeline(self):
    baseCommit = "a" * 40
    commit = "c" * 40
    rawPath = "1-raw/Joe主动收录/AI资讯/2026-08-04__note.md"
    remoteReads = iter([baseCommit, baseCommit])
    calls = []

    async def fakeGitOutput(repoRoot, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] in {"fetch", "push"}:
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return commit
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return next(remoteReads)
      if args[:2] == ("rev-parse", f"{commit}^"):
        return baseCommit
      if args[0] == "diff-tree":
        return f"{rawPath}\0"
      raise AssertionError(args)

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      target = repoRoot / rawPath
      target.parent.mkdir(parents=True)
      target.write_text("committed managed content\n", encoding="utf-8")
      journalPath = repoRoot / "publisher-journal.json"
      self.writeJournal(
        journalPath,
        state="git-committed",
        baseCommit=baseCommit,
        paths=[rawPath],
        repoRoot=repoRoot,
        commit=commit,
      )

      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "changed_paths", return_value=[]),
        mock.patch.object(MODULE, "run_command") as pipeline,
      ):
        result = await MODULE.publish(
          repoRoot,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=repoRoot / "publisher.lock",
          journal_path=journalPath,
        )

      pipeline.assert_not_called()
      self.assertTrue(result["resumed"])
      self.assertTrue(result["pushed"])
      self.assertFalse(journalPath.exists())
      self.assertIn(("push", "origin", "HEAD:refs/heads/main"), calls)

  async def test_push_ack_loss_is_recognized_without_second_push(self):
    baseCommit = "a" * 40
    commit = "c" * 40
    rawPath = "1-raw/Joe主动收录/AI资讯/2026-08-04__note.md"
    calls = []

    async def fakeGitOutput(repoRoot, *args):
      calls.append(args)
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] == "fetch":
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return commit
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return commit
      if args[:2] == ("rev-parse", f"{commit}^"):
        return baseCommit
      if args[0] == "diff-tree":
        return f"{rawPath}\0"
      if args[0] == "push":
        raise AssertionError("push must not repeat after remote contains owned commit")
      raise AssertionError(args)

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      target = repoRoot / rawPath
      target.parent.mkdir(parents=True)
      target.write_text("committed managed content\n", encoding="utf-8")
      journalPath = repoRoot / "publisher-journal.json"
      self.writeJournal(
        journalPath,
        state="git-committed",
        baseCommit=baseCommit,
        paths=[rawPath],
        repoRoot=repoRoot,
        commit=commit,
      )

      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "changed_paths", return_value=[]),
      ):
        result = await MODULE.publish(
          repoRoot,
          remote="origin",
          branch="main",
          pipeline=MODULE.DEFAULT_PIPELINE,
          lock_path=repoRoot / "publisher.lock",
          journal_path=journalPath,
        )

      self.assertTrue(result["pushRecovered"])
      self.assertFalse(journalPath.exists())
      self.assertFalse(any(call[0] == "push" for call in calls))

  async def test_pipeline_complete_hash_mismatch_stops_recovery(self):
    baseCommit = "a" * 40
    rawPath = "1-raw/Joe主动收录/AI资讯/2026-08-04__note.md"

    async def fakeGitOutput(repoRoot, *args):
      if args[:3] == ("config", "--get", "remote.origin.url"):
        return "git@example.test:joe/waic.git"
      if args[0] == "fetch":
        return ""
      if args[:2] == ("rev-parse", "HEAD"):
        return baseCommit
      if args[:2] == ("rev-parse", "refs/remotes/origin/main"):
        return baseCommit
      raise AssertionError(args)

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      (repoRoot / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
      target = repoRoot / rawPath
      target.parent.mkdir(parents=True)
      target.write_text("owned content\n", encoding="utf-8")
      journalPath = repoRoot / "publisher-journal.json"
      self.writeJournal(
        journalPath,
        state="pipeline-complete",
        baseCommit=baseCommit,
        paths=[rawPath],
        repoRoot=repoRoot,
      )
      target.write_text("external change\n", encoding="utf-8")

      with (
        mock.patch.object(MODULE, "git_output", side_effect=fakeGitOutput),
        mock.patch.object(MODULE, "changed_paths", return_value=[rawPath]),
        mock.patch.object(MODULE, "run_command") as pipeline,
      ):
        with self.assertRaisesRegex(MODULE.PublishError, "hashes changed"):
          await MODULE.publish(
            repoRoot,
            remote="origin",
            branch="main",
            pipeline=MODULE.DEFAULT_PIPELINE,
            lock_path=repoRoot / "publisher.lock",
            journal_path=journalPath,
          )

      pipeline.assert_not_called()
      self.assertTrue(journalPath.exists())

  async def test_real_git_worktree_resumes_pipeline_complete_journal(self):
    def git(cwd: Path, *args: str) -> str:
      process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=True,
        text=True,
      )
      return process.stdout.strip()

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      remoteRoot = root / "remote.git"
      seedRoot = root / "seed"
      worktreeRoot = root / "worktree"
      remoteRoot.mkdir()
      seedRoot.mkdir()
      git(remoteRoot, "init", "--bare")
      git(seedRoot, "init", "-b", "main")
      git(seedRoot, "config", "user.name", "Automation Test")
      git(seedRoot, "config", "user.email", "automation@example.test")

      ledgerPath = "3-processing/index/intake-ledger.jsonl"
      seedLedger = seedRoot / ledgerPath
      seedLedger.parent.mkdir(parents=True)
      seedLedger.write_text("baseline\n", encoding="utf-8")
      git(seedRoot, "add", "--", ledgerPath)
      git(seedRoot, "commit", "-m", "seed")
      git(seedRoot, "remote", "add", "origin", str(remoteRoot))
      git(seedRoot, "push", "-u", "origin", "main")
      baseCommit = git(seedRoot, "rev-parse", "HEAD")
      git(seedRoot, "worktree", "add", "--detach", str(worktreeRoot), baseCommit)

      worktreeLedger = worktreeRoot / ledgerPath
      worktreeLedger.write_text("baseline\nnew managed intake\n", encoding="utf-8")
      journalPath = root / "publisher-journal.json"
      self.writeJournal(
        journalPath,
        state="pipeline-complete",
        baseCommit=baseCommit,
        paths=[ledgerPath],
        repoRoot=worktreeRoot,
      )

      result = await MODULE.publish(
        worktreeRoot,
        remote="origin",
        branch="main",
        pipeline=MODULE.DEFAULT_PIPELINE,
        lock_path=root / "publisher.lock",
        journal_path=journalPath,
      )

      remoteCommit = git(remoteRoot, "rev-parse", "refs/heads/main")
      self.assertTrue(result["resumed"])
      self.assertTrue(result["pushed"])
      self.assertNotEqual(result["commit"], baseCommit)
      self.assertEqual(remoteCommit, result["commit"])
      self.assertFalse(journalPath.exists())


if __name__ == "__main__":
  unittest.main()
