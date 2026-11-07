import json
import os
import argparse

STATE_FILE = "deployment_state.json"

ENVIRONMENTS = ["dev", "testing", "staging", "prod"]

# Initial deployment information
DEFAULT_STATE = {
    env: {
        "active_version": "v1.0",
        "previous_version": None,
        "active_slot": "blue",
        "slots": {
            "blue": "v1.0",
            "green": None
        }
    }
    for env in ENVIRONMENTS
}


# Load deployment information
def load_state():
    if not os.path.exists(STATE_FILE):
        return json.loads(json.dumps(DEFAULT_STATE))

    try:
        with open(STATE_FILE, "r") as file:
            content = file.read().strip()

            if not content:
                return json.loads(json.dumps(DEFAULT_STATE))

            state = json.loads(content)

            for env in ENVIRONMENTS:
                if env not in state:
                    state[env] = json.loads(
                        json.dumps(DEFAULT_STATE[env])
                    )

            return state

    except (json.JSONDecodeError, OSError):
        print("Invalid state file. Initializing default state.")
        return json.loads(json.dumps(DEFAULT_STATE))


# Save deployment information
def save_state(state):
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=4)


# Display deployment status
def show_status(state):

    print("\n========== DEPLOYMENT STATUS ==========")

    for env, details in state.items():

        print(f"\nEnvironment: {env.upper()}")
        print("Active Version:", details["active_version"])
        print("Previous Version:", details["previous_version"])
        print("Active Slot:", details["active_slot"])

    print("\n=======================================")


# Deploy application
def deploy(env, version, strategy, fail_health, auto_approve):

    state = load_state()

    if env not in ENVIRONMENTS:
        print("Invalid environment!")
        return

    current = state[env]

    print("\n========== DEPLOYMENT STARTED ==========")
    print("Environment:", env.upper())
    print("New Version:", version)
    print("Strategy:", strategy.upper())
    print("Current Version:", current["active_version"])

    # Production approval
    if env == "prod" and not auto_approve:

        approval = input(
            "\nApprove production deployment? (yes/no): "
        ).strip().lower()

        if approval != "yes":
            print("Deployment cancelled: approval not granted.")
            return

    old_version = current["active_version"]

    # DIRECT DEPLOYMENT
    if strategy == "direct":

        print("\nDeploying application directly...")

        if fail_health:
            print("Health check FAILED!")
            print("Deployment stopped. Previous version remains active.")
            return

        current["previous_version"] = old_version
        current["active_version"] = version

    # BLUE-GREEN DEPLOYMENT
    elif strategy == "blue-green":

        active_slot = current["active_slot"]

        inactive_slot = (
            "green" if active_slot == "blue" else "blue"
        )

        print(f"\nCurrent active slot: {active_slot}")

        print(f"Deploying {version} to {inactive_slot} slot...")

        current["slots"][inactive_slot] = version

        print("Testing the new slot...")

        if fail_health:
            print("Health check FAILED!")
            print("Keeping the old slot active.")
            return

        print("Health check PASSED!")
        print("Switching traffic to the new slot...")

        current["previous_version"] = old_version
        current["active_version"] = version
        current["active_slot"] = inactive_slot

        print("Traffic successfully switched.")

    # CANARY DEPLOYMENT
    elif strategy == "canary":

        print("\nStarting Canary Deployment...")

        traffic_stages = [10, 25, 50, 100]

        for percentage in traffic_stages:

            print(f"\nSending {percentage}% traffic to {version}...")

            if fail_health and percentage == 25:

                print("Health check FAILED!")
                print("Stopping the canary release.")
                print("Rolling back to:", old_version)
                print("100% traffic remains on the old version.")
                return

            print(f"Health check PASSED at {percentage}% traffic.")

        current["previous_version"] = old_version
        current["active_version"] = version

        print("\nCanary deployment completed successfully.")

    else:
        print("Invalid deployment strategy!")
        return

    save_state(state)

    print("\nDEPLOYMENT SUCCESSFUL!")
    print("Active Version:", current["active_version"])
    print("Previous Version:", current["previous_version"])
    print("========================================")


# Rollback deployment
def rollback(env):

    state = load_state()

    if env not in ENVIRONMENTS:
        print("Invalid environment!")
        return

    current = state[env]

    previous = current["previous_version"]

    if previous is None:
        print("No previous version available for rollback.")
        return

    print("\n========== ROLLBACK STARTED ==========")

    print("Current Version:", current["active_version"])
    print("Restoring Version:", previous)

    current["active_version"] = previous
    current["previous_version"] = None

    if current["active_slot"] in current["slots"]:
        current["slots"][current["active_slot"]] = previous

    save_state(state)

    print("Rollback SUCCESSFUL!")
    print("Active Version:", current["active_version"])
    print("======================================")


# Main function
def main():

    parser = argparse.ArgumentParser(
        description="Python CD Deployment Simulator"
    )

    parser.add_argument(
        "action",
        choices=["deploy", "status", "rollback"]
    )

    parser.add_argument(
        "--env",
        choices=ENVIRONMENTS
    )

    parser.add_argument(
        "--version"
    )

    parser.add_argument(
        "--strategy",
        choices=["direct", "blue-green", "canary"],
        default="direct"
    )

    parser.add_argument(
        "--fail-health",
        action="store_true",
        help="Simulate a failed health check"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip manual production approval"
    )

    args = parser.parse_args()

    if args.action == "status":

        show_status(load_state())

    elif args.action == "deploy":

        if not args.env or not args.version:
            parser.error("deploy requires --env and --version")

        deploy(
            args.env,
            args.version,
            args.strategy,
            args.fail_health,
            args.auto_approve
        )

    elif args.action == "rollback":

        if not args.env:
            parser.error("rollback requires --env")

        rollback(args.env)


if __name__ == "__main__":
    main()