import subprocess
import time

class ExecuteLinuxCommand:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "command": ("STRING", {
                    "default": "ls -la",
                    "multiline": True
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"

    # >>> Your request: Make it a final output node <<<
    OUTPUT_NODE = True

    CATEGORY = "utils/system"

    def run(self, command):
        print(f"\n--- [ExecuteLinuxCommand] Running: {command} ---\n", flush=True)

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )
            stdout, stderr = process.communicate()

            output = ""
            if stdout:
                output += stdout
            if stderr:
                output += "\n[ERROR]\n" + stderr

            # Log to terminal
            print(f"--- [ExecuteLinuxCommand Output] ---\n{output}\n", flush=True)

            # Return text to API
            return (output,)

        except Exception as e:
            error_text = f"Exception: {str(e)}"
            print(f"--- [ExecuteLinuxCommand ERROR] ---\n{error_text}\n", flush=True)
            return (error_text,)

    @classmethod
    def IS_CHANGED(s, command):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "ExecuteLinuxCommand": ExecuteLinuxCommand
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ExecuteLinuxCommand": "Execute Linux Command"
}
