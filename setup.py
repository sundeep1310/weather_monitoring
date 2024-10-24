import os
import sys
from pathlib import Path
import shutil
import json

class ProjectSetup:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.required_dirs = [
            "src",
            "src/dashboard",
            "src/dashboard/templates",
            "static",
            "tests",
        ]
        self.required_files = [
            ".env",
            "requirements.txt",
            "docker-compose.yml",
            "main.py",
            "run.py"
        ]
        self.template_files = {
            "src/dashboard/templates/index.html": "",
            "src/dashboard/templates/alerts.html": "",
            "static/style.css": "",
        }

    def create_directories(self):
        """Create all required directories."""
        print("\n📁 Creating directories...")
        for directory in self.required_dirs:
            dir_path = self.root_dir / directory
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created {directory}")
            except Exception as e:
                print(f"❌ Error creating {directory}: {str(e)}")
                return False
        return True

    def create_init_files(self):
        """Create __init__.py files in Python packages."""
        print("\n📄 Creating __init__.py files...")
        init_locations = ["src", "tests", "src/dashboard"]
        for location in init_locations:
            init_file = self.root_dir / location / "__init__.py"
            try:
                init_file.touch()
                print(f"✅ Created {location}/__init__.py")
            except Exception as e:
                print(f"❌ Error creating {location}/__init__.py: {str(e)}")
                return False
        return True

    def create_env_template(self):
        """Create .env.template file with required variables."""
        print("\n📄 Creating .env.template...")
        env_template = """OPENWEATHERMAP_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@db:5432/weather_db
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_TEMPERATURE_THRESHOLD=35.0
CONSECUTIVE_ALERTS_REQUIRED=2
"""
        try:
            with open(self.root_dir / ".env.template", "w") as f:
                f.write(env_template)
            print("✅ Created .env.template")
            
            # Create actual .env file if it doesn't exist
            env_file = self.root_dir / ".env"
            if not env_file.exists():
                shutil.copy2(self.root_dir / ".env.template", env_file)
                print("✅ Created .env from template")
        except Exception as e:
            print(f"❌ Error creating environment files: {str(e)}")
            return False
        return True

    def create_vscode_settings(self):
        """Create VS Code settings for better development experience."""
        print("\n⚙️ Creating VS Code settings...")
        vscode_dir = self.root_dir / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        settings = {
            "python.linting.enabled": True,
            "python.linting.pylintEnabled": True,
            "python.formatting.provider": "black",
            "editor.formatOnSave": True,
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
            "python.testing.nosetestsEnabled": False,
            "python.testing.pytestArgs": [
                "tests"
            ]
        }
        
        launch = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: FastAPI",
                    "type": "python",
                    "request": "launch",
                    "module": "uvicorn",
                    "args": [
                        "main:app",
                        "--reload",
                        "--port",
                        "8000"
                    ],
                    "jinja": True,
                    "justMyCode": True
                }
            ]
        }

        try:
            with open(vscode_dir / "settings.json", "w") as f:
                json.dump(settings, f, indent=4)
            with open(vscode_dir / "launch.json", "w") as f:
                json.dump(launch, f, indent=4)
            print("✅ Created VS Code settings")
        except Exception as e:
            print(f"❌ Error creating VS Code settings: {str(e)}")
            return False
        return True

    def verify_setup(self):
        """Verify that all required files and directories exist."""
        print("\n🔍 Verifying setup...")
        all_good = True
        
        # Check directories
        for directory in self.required_dirs:
            dir_path = self.root_dir / directory
            if not dir_path.is_dir():
                print(f"❌ Missing directory: {directory}")
                all_good = False
        
        # Check files
        for file in self.required_files:
            file_path = self.root_dir / file
            if not file_path.is_file():
                print(f"⚠️ Note: {file} needs to be created manually")
        
        if all_good:
            print("✅ All required directories are present")
            print("\n⚠️ Note: Some files need to be created manually:")
            print("1. main.py - Copy from the provided main.py")
            print("2. requirements.txt - Make sure it's updated")
            print("3. docker-compose.yml - Copy from the provided file")
            print("4. Update .env with your credentials")
        return all_good

    def setup(self):
        """Run the complete setup process."""
        print("🚀 Starting project setup...")
        
        steps = [
            self.create_directories,
            self.create_init_files,
            self.create_env_template,
            self.create_vscode_settings,
            self.verify_setup
        ]
        
        for step in steps:
            if not step():
                print("\n❌ Setup failed!")
                return False
        
        print("\n✨ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update the .env file with your actual credentials")
        print("2. Install requirements: pip install -r requirements.txt")
        print("3. Start the PostgreSQL container: docker-compose up -d")
        print("4. Run the application: python -m uvicorn main:app --reload")
        return True

if __name__ == "__main__":
    setup = ProjectSetup()
    setup.setup()