# Synthetic bidirectional ELS and RX-ring feedback

## Architecture

Four local RX-ring PI loops respond first to preserve alignment. The median of
their actuator corrections estimates common laser drift. A slower outer loop
moves the shared external-laser setpoint and releases local heater range.

```text
shared ELS -> 4 RX rings -> receivers
     ^            |
     +-- robust common-correction telemetry
```

Median aggregation is intentional: one abnormal lane should not steer the
shared laser as strongly as it would under a simple mean.

## Run

```powershell
& .\.venv\Scripts\python.exe scripts\run_bidirectional_els_rx_feedback.py
& .\.venv\Scripts\python.exe scripts\run_bidirectional_els_rx_robustness.py
```

The scripts compare no control, RX-only and joint control, then sweep feedback
delay/gain, actuator capture, a one-lane outlier, sensor noise and quantization.
Outputs are written under `results/bidirectional_els_rx_*`.

## Calibration boundary

Every checked-in value is synthetic. Hardware use requires authorized values
for ELS command gain/range/step response, RX monitor-to-detuning transfer,
heater gain/range/step response, telemetry timing/error and the mapping from
residual detuning to link penalty.

This is a slow wavelength-control model. RIN and phase/frequency noise outside
the loop bandwidth remain link disturbances; successful feedback is not
phase-noise cancellation.
