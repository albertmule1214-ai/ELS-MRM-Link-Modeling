# Configuration policy

Committed configuration files must contain only public examples or synthetic assumptions, and every physical scalar must include `source` and `ref` metadata.

Use these source labels:

- `PUBLIC_SPEC`: public standard or implementation agreement.
- `PUBLIC_LITERATURE_EXAMPLE`: published example that is not assumed to match a target device.
- `MODEL`: a mathematical convention or implementation choice.
- `ASSUMPTION`: synthetic placeholder used to make the example runnable.
- `MEASURED`: permitted only in approved internal storage, not this repository.

Put project-specific parameters in `configs/local/`. That directory is ignored by Git. Scripts should accept a `--config` argument before local configurations become part of the workflow.

