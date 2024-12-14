from bioexperiment_suite.experiment.collections import Relation, Statistic
from bioexperiment_suite.experiment import Experiment, Condition
from bioexperiment_suite.tools import get_connected_devices


# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes

FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pumps in mL/min

PUMP_OUT_VOLUME_ML = 5
PUMP_FOOD_VOLUME_ML = 2
PUMP_DRUG_VOLUME_ML = 2

OPTICAL_DENSITY_THRESHOLD = 0.5

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
)  # Number of solution refreshes
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)  # Number of measurements per refresh


# Retrieve connected devices by checking the serial ports
pumps, spectrophotometers = get_connected_devices()

# Unpack discovered devices
(spectrophotometer,) = spectrophotometers  # Suppose we have one spectrophotometer

# Comparison of found pumps
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
    output_dir=".",  # Define the output directory here before running the script
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
experiment.add_action(
    pump_food.pour_in_volume, volume=PUMP_FOOD_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=IN
)

# Add the main experiment loop
for _ in range(n_solution_refreshes):  # Loop over the number of solution refreshes
    for _ in range(n_measurements_per_solution_refresh):  # Loop over the number of measurements per refresh
        experiment.add_measurement(spectrophotometer.measure_optical_density, measurement_name=OPTICAL_DENSITY)
        experiment.add_measurement(spectrophotometer.get_temperature, measurement_name=TEMPERATURE)

        experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)  # Wait for the measurement interval

    experiment.add_action(
        pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
    )

    # Add the actions to pour in the drug or food based on the condition
    experiment.add_action(
        pump_drug.pour_in_volume,
        volume=PUMP_DRUG_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_exceeded_threshold,  # Only add the drug if the OD exceeded the threshold
    )
    experiment.add_action(
        pump_food.pour_in_volume,
        volume=PUMP_FOOD_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_not_exceeded_threshold,  # Only add the food if the OD did not exceed the threshold
    )

experiment.start(start_in_background=False)  # Start the experiment in idle mode
