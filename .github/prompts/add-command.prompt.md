---
mode: ask
---

Add a new CLI command to `dnafx-preset` following the existing `set` command pattern.

**Reference implementation:** `set` command in `src/dnafx_preset/cli.py` and `tests/test_cli.py`.

## Steps

1. **Add the subparser** in `build_parser()` in `cli.py`:
   ```python
   my_parser = subparsers.add_parser("my-command", help="...")
   my_parser.add_argument(...)
   ```

2. **Add a handler function** that takes `(args: Namespace, stdout: TextIO) -> int`:
   ```python
   def handle_my_command(args: Namespace, stdout: TextIO) -> int:
       client = build_client(args)
       # ... call client methods ...
       stdout.write("...\n")
       return 0
   ```

3. **Wire into `main()`** dispatch block:
   ```python
   if args.command == "my-command":
       return handle_my_command(args, resolved_stdout)
   ```

4. **Write a test** in `tests/test_cli.py` by patching the factory:
   ```python
   def test_my_command_uses_client() -> None:
       stdout = StringIO()
       with patch("dnafx_preset.cli.build_client", return_value=FakeClient()):
           exit_code = main(["my-command", ...], stdout=stdout)
       assert exit_code == 0
       assert "expected output" in stdout.getvalue()
   ```

## Constraints

- Handler functions must be pure functions of their arguments — no global state.
- Use `build_client(args)` for USB operations; do not construct `DnafxPresetClient` directly inside handlers.
- The exit code must be `0` on success and `1` on error (the `main()` wrapper catches exceptions and writes to stderr).
- Do not add a factory for the new command unless it has injectable dependencies beyond `build_client`.
