import binascii
import os
from kubernetes import client


class CreateProcessVideoJob:
    def __init__(self, filename):
        self.filename = filename
        self.job_name = binascii.hexlify(os.urandom(16)).decode('utf-8')
        self.job = None
        self.batch_v1 = client.BatchV1Api()

    def create_job_object(self):
        env_vars = [
            client.V1EnvVar(name="MONGO_HOST", value="mongo"),
            client.V1EnvVar(name="MONGO_PORT", value="27017"),
        ]
        # Configure Pod template container
        container = client.V1Container(
            name=self.job_name,
            image="jdvincent/batch-process-image:latest",
            command=["python", "main.py", "--filename", self.filename],
            env=env_vars)
        # Create and configure a spec section
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": self.job_name}),
            spec=client.V1PodSpec(restart_policy="Never", containers=[container]))
        # Create the specification of deployment
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=4)
        # Instantiate the job object
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=spec)

        self.job = job

    def create_job(self):
        api_response = self.batch_v1.create_namespaced_job(
            body=self.job,
            namespace="default")
        print("Job created. status='%s'" % str(api_response.status))
