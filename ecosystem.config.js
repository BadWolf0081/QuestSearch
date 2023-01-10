module.exports = {
  apps: [
    {
      name: "QuestSearch",
      script: "/home/your_username/QuestSearch/your_venv_dir/bin/python3 qs.py",
      cwd: "/home/your_username/QuestSearch/",
      instances: 1,
      autorestart: true,
      max_memory_restart: "1G",
      env_production: {
        NODE_ENV: "production",
      },
    },
  ],
};
