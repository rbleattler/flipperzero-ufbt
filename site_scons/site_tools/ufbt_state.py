from SCons.Errors import SConsEnvironmentError

import json
import os
from functools import reduce


def _load_sdk_data(sdk_root):
    sdk_data = {}
    with open(os.path.join(sdk_root, "sdk.opts")) as f:
        sdk_json_data = json.load(f)
        replacements = {
            sdk_json_data["app_ep_subst"]: "${APP_ENTRY}",
            sdk_json_data["sdk_path_subst"]: sdk_root.replace("\\", "/"),
        }

        for key, value in sdk_json_data.items():
            if key in (
                "cc_args",
                "cpp_args",
                "linker_args",
                "linker_libs",
                "sdk_symbols",
            ):
                sdk_data[key] = reduce(
                    lambda a, kv: a.replace(*kv), replacements.items(), value
                ).split(" ")
            else:
                sdk_data[key] = value

    return sdk_data


def generate(env, **kw):
    sdk_state_dir = kw.get("SDK_STATE_DIR", ".ufbt/current")
    sdk_meta_filename = kw.get("SDK_META", "sdk_state.json")

    sdk_meta_path = os.path.join(sdk_state_dir, sdk_meta_filename)
    if not os.path.exists(sdk_meta_path):
        raise SConsEnvironmentError(f"SDK state file {sdk_meta_path} not found")

    with open(sdk_meta_path, "r") as f:
        sdk_state = json.load(f)

    if not (sdk_components := sdk_state.get("components", {})):
        raise SConsEnvironmentError("SDK state file doesn't contain components data")

    sdk_options_path = os.path.join(sdk_state_dir, sdk_components.get("sdk", "sdk"))
    sdk_data = _load_sdk_data(sdk_options_path)
    if not sdk_state["meta"]["hw_target"].endswith(sdk_data["hardware"]):
        raise SConsEnvironmentError("SDK state file doesn't match hardware target")

    env.SetDefault(
        FIRMWARE_BUILD_CFG="firmware",
        TARGET_HW=int(sdk_data["hardware"]),
        CFLAGS_APP=sdk_data["cc_args"],
        CXXFLAGS_APP=sdk_data["cpp_args"],
        LINKFLAGS_APP=sdk_data["linker_args"],
        LIBS=sdk_data["linker_libs"],
        # Paths
        SDK_DEFINITION=env.File(sdk_data["sdk_symbols"][0]),
        FBT_SCRIPT_DIR=env.Dir(
            os.path.join(sdk_state_dir, sdk_components.get("scripts", "."), "scripts")
        ),
        LIBPATH=env.Dir(os.path.join(sdk_state_dir, sdk_components.get("lib", "lib"))),
        FW_ELF=env.File(os.path.join(sdk_state_dir, sdk_components.get("elf"))),
        FW_BIN=env.File(os.path.join(sdk_state_dir, sdk_components.get("fwbin"))),
    )


def exists(env):
    return True
