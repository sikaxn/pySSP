# Development Notes

This section tracks engineering notes for improving reliability and automated testing.

## Auto-test roadmap

```{toctree}
:maxdepth: 1

auto_test_plan
audio_playback_stack
```

## Policy

- New bug fixes should include a regression test.
- Core regression tests are required in CI.
- Full-suite coverage runs in CI as advisory until all current failures are stabilized.
