# Xtreamly ACP Agent

This project contains the ACP (Automated Control Pipeline) agent for Xtreamly.

---

## 🛠️ Development

1. Create `.env` file based on `.env.example`  
2. Run the app and tests in two terminals:
   - Terminal 1:  
     ```bash
     python main.py
     ```
   - Terminal 2:  
     ```bash
     python test.py
     ```

---

## 🚀 Deployment

1. Create `.env` file based on `.env.example`  
2. **Build Docker image**:
   ```bash
   sudo docker build -t xtreamly-acp-image .
   ```

3. **Tag Docker image**:
   ```bash
   sudo docker tag xtreamly-acp-image us-central1-docker.pkg.dev/xtreamly-ai/long-running/xtreamly-acp-agent
   ```

4. **Push Docker image**:
   ```bash
   sudo docker push us-central1-docker.pkg.dev/xtreamly-ai/long-running/xtreamly-acp-agent
   ```

5. **Deploy to Kubernetes**:
   ```bash
   kubectl apply -f deployment.yaml -n xtreamly-acp-agent
   ```
