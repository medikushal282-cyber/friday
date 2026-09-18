import docker
import os
import tempfile
import uuid

class DockerSandbox:
    def __init__(self, image="python:3.11-slim"):
        self.client = docker.from_env()
        self.image = image
        
        # Ensure image exists locally
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            print(f"Pulling sandbox image {self.image}...")
            self.client.images.pull(self.image)

    def execute_python(self, code: str, timeout: int = 30, memory_limit: str = "512m", network: bool = False) -> dict:
        """Executes python code in an isolated container."""
        temp_dir = tempfile.mkdtemp()
        script_path = os.path.join(temp_dir, "main.py")
        
        with open(script_path, "w") as f:
            f.write(code)

        container_name = f"fraiday_sandbox_{uuid.uuid4().hex[:8]}"
        
        try:
            container = self.client.containers.run(
                self.image,
                command=["python", "/workspace/main.py"],
                name=container_name,
                volumes={temp_dir: {'bind': '/workspace', 'mode': 'ro'}},
                working_dir="/workspace",
                mem_limit=memory_limit,
                network_disabled=not network,
                detach=True
            )
            
            result = container.wait(timeout=timeout)
            logs = container.logs().decode("utf-8")
            
            return {
                "exit_code": result["StatusCode"],
                "stdout": logs,
                "error": None
            }
            
        except docker.errors.ContainerError as e:
            return {
                "exit_code": e.exit_status,
                "stdout": e.container.logs().decode("utf-8"),
                "error": str(e)
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "error": str(e)
            }
        finally:
            try:
                container = self.client.containers.get(container_name)
                container.remove(force=True)
            except Exception:
                pass
            
            try:
                os.remove(script_path)
                os.rmdir(temp_dir)
            except Exception:
                pass
