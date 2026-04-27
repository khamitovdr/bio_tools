#!/usr/bin/env python
# coding: utf-8

from bioexperiment_suite.experiment.collections import Relation, Statistic
from bioexperiment_suite.experiment import Experiment, Condition
from bioexperiment_suite.interfaces import LabDevicesClient


# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes
INWARDS_PUMP_DELAY_SEC = 10  # Delay before "food" or "drug" pump strts working

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes

FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pumps in mL/min

PUMP_OUT_VOLUME_ML = 5
PUMP_FOOD_VOLUME_ML = 2
PUMP_DRUG_VOLUME_ML = 2

OPTICAL_DENSITY_THRESHOLD = 0.5

LAB_DEVICES_PORT = 9001  # Per-lab-machine chisel-tunnel port

# Define measurements
OPTICAL_DENSITY = "optical_density"
TEMPERATURE = "temperature"

# Define pump rotation directions
IN = "right"
OUT = "left"


# Ensure intervals are valid
assert (
    SOLUTION_REFRESH_INTERVAL_MIN % MEASUREMENT_INTERVAL_MINUTES == 0
), "Solution refresh interval should be a multiple of measurement interval"
assert (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60
) % SOLUTION_REFRESH_INTERVAL_MIN == 0, "Total experiment duration should be a multiple of solution refresh interval"

# Calculate the number of solution refreshes and measurements per refresh
n_solution_refreshes = (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60 // SOLUTION_REFRESH_INTERVAL_MIN
)
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)
delay_time = (PUMP_OUT_VOLUME_ML / FLOW_RATE_ML_PER_MINUTE) * 60 + 1 + INWARDS_PUMP_DELAY_SEC


# Connect to the lab devices service and discover devices
client = LabDevicesClient(port=LAB_DEVICES_PORT)
devices = client.discover()

(densitometer,) = devices.densitometers  # Suppose we have one densitometer
pumps = devices.pumps


# Comparison of found pumps
assert len(pumps) == 3, f"{len(pumps)} pumps found! Exactly 3 pumps is needed for this experiment"
print("""
Please choose the role of currently rotating pump:

1. Pump for removing waste
2. Pump for feeding the bacteria
3. Pump for adding the drug
""")
for pump in pumps:
    pump.set_default_flow_rate(1)
    pump.start_continuous_rotation(0.1)

    role = input("Enter the number and press Enter: ")
    if role == "1":
        pump_out = pump
    elif role == "2":
        pump_food = pump
    elif role == "3":
        pump_drug = pump
    else:
        print("Invalid input. Please enter a number between 1 and 3")

    pump.stop_continuous_rotation()


for name in ["pump_out", "pump_food", "pump_drug"]:
    assert name in locals(), f"Please assign a pump to the variable {name}"


# Initialize the experiment
experiment = Experiment(
    output_dir=".",
)

# Define the metrics
optical_density_last_value = experiment.create_metric(
    measurement_name=OPTICAL_DENSITY,
    statistic=Statistic.LAST(),
)

# Define the conditions
od_exceeded_threshold = Condition(
    metric=optical_density_last_value,
    relation=Relation.GREATER_THAN(OPTICAL_DENSITY_THRESHOLD),
)
od_not_exceeded_threshold = od_exceeded_threshold.negation


# Add the initial actions to pour out the excessive solution and pour in the food
experiment.add_action(
    pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
)
experiment.add_wait(delay_time)
experiment.add_action(
    pump_food.pour_in_volume, volume=PUMP_FOOD_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=IN
)

# Add the main experiment loop
for _ in range(n_solution_refreshes):
    for i in range(n_measurements_per_solution_refresh):
        wait_time = (
            MEASUREMENT_INTERVAL_MINUTES * 60 - delay_time
            if i == 0 else MEASUREMENT_INTERVAL_MINUTES * 60
        )
        experiment.add_wait(wait_time)

        experiment.add_measurement(densitometer.measure_optical_density, measurement_name=OPTICAL_DENSITY)
        experiment.add_measurement(densitometer.get_temperature, measurement_name=TEMPERATURE)

    experiment.add_action(
        pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
    )
    experiment.add_wait(delay_time)

    experiment.add_action(
        pump_drug.pour_in_volume,
        volume=PUMP_DRUG_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_exceeded_threshold,
        info_log_message="Drug added",
    )
    experiment.add_action(
        pump_food.pour_in_volume,
        volume=PUMP_FOOD_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_not_exceeded_threshold,
        info_log_message="Food added",
    )


experiment.start(start_in_background=False)
