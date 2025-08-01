Development:
0- Create .env based on .env.example
1- Test by running main.py in one shell and test.py in other

Deployment
0- Create .env based on .env.example
1- Build docker image:
sudo docker build -t xtreamly-acp-image .
2- Tag image:
sudo docker tag xtreamly-acp-image us-central1-docker.pkg.dev/xtreamly-ai/long-running/xtreamly-acp-agent
3- Push image:
sudo docker push us-central1-docker.pkg.dev/xtreamly-ai/long-running/xtreamly-acp-agent
4- Deploy to kubernetes
kubectl apply -f deployment.yaml -n xtreamly-acp-agent
