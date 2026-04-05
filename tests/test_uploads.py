import unittest

from leave_app import create_app
from leave_app.services.uploads import build_object_storage_client_kwargs, storage_key


class UploadConfigTestCase(unittest.TestCase):
    def test_oci_storage_config_maps_to_s3_compatible_client(self):
        app = create_app(
            {
                "TESTING": True,
                "STORAGE_BACKEND": "oci",
                "OCI_OBJECT_STORAGE_REGION": "us-ashburn-1",
                "OCI_OBJECT_STORAGE_BUCKET": "permitrack-bucket",
                "OCI_OBJECT_STORAGE_PREFIX": "permitrack",
                "OCI_OBJECT_STORAGE_ENDPOINT": "https://namespace.compat.objectstorage.us-ashburn-1.oraclecloud.com",
                "OCI_S3_ACCESS_KEY": "access-key",
                "OCI_S3_SECRET_KEY": "secret-key",
            }
        )

        with app.app_context():
            self.assertEqual(app.config["STORAGE_BACKEND"], "oci")
            self.assertEqual(app.config["STORAGE_BUCKET"], "permitrack-bucket")
            self.assertEqual(app.config["STORAGE_PREFIX"], "permitrack")
            self.assertEqual(
                app.config["STORAGE_ENDPOINT_URL"],
                "https://namespace.compat.objectstorage.us-ashburn-1.oraclecloud.com",
            )
            self.assertEqual(app.config["STORAGE_ADDRESSING_STYLE"], "path")
            client_kwargs = build_object_storage_client_kwargs()
            self.assertEqual(client_kwargs["endpoint_url"], app.config["STORAGE_ENDPOINT_URL"])
            self.assertEqual(client_kwargs["aws_access_key_id"], "access-key")
            self.assertEqual(client_kwargs["aws_secret_access_key"], "secret-key")
            self.assertEqual(storage_key("leave_proofs", "proof.pdf"), "permitrack/leave_proofs/proof.pdf")


if __name__ == "__main__":
    unittest.main()
