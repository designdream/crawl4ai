# CI/CD Setup for Crawl4AI

This guide explains how to set up continuous integration and deployment for your Crawl4AI application to automate deployments to your Digital Ocean server.

## Prerequisites

1. GitHub account with your Crawl4AI repository
2. Docker Hub account for storing Docker images
3. SSH access to your Digital Ocean server (164.92.69.88)

## Setup Steps

### 1. Create Required GitHub Secrets

In your GitHub repository, go to Settings > Secrets and variables > Actions and add the following secrets:

| Secret Name | Description |
|-------------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | A Docker Hub access token (create one at https://hub.docker.com/settings/security) |
| `SSH_PRIVATE_KEY` | Your private SSH key for accessing the Digital Ocean server |
| `CRAWL4AI_SECRET_KEY` | The JWT secret key for authentication (currently: `d68124424f40a43aa20606431f13e9ed918771badac97f001a82d4f681f6f391`) |

### 2. Generate SSH Key for GitHub Actions (if needed)

If you don't already have an SSH key pair for GitHub Actions to access your server:

```bash
# Generate a new key pair
ssh-keygen -t rsa -b 4096 -f github-actions-key -N ""

# Copy the public key to your server
ssh-copy-id -i github-actions-key.pub root@164.92.69.88

# Add the private key to GitHub Secrets as SSH_PRIVATE_KEY
cat github-actions-key
```

### 3. Docker Hub Setup

1. Create an account at [Docker Hub](https://hub.docker.com/) if you don't have one
2. Create a new repository named "crawl4ai"
3. Generate an access token at Docker Hub > Account Settings > Security

### 4. Push Your Code to GitHub

Make sure your code is pushed to GitHub and the repository has the `.github/workflows/deploy.yml` file.

### 5. Verify the Workflow

After pushing your code to the main branch:

1. Go to the "Actions" tab in your GitHub repository
2. You should see the "Deploy Crawl4AI" workflow running
3. Wait for it to complete and check if it successfully deployed

## Manual Deployment

If you need to manually trigger the deployment:

1. Go to the "Actions" tab in your GitHub repository
2. Select the "Deploy Crawl4AI" workflow
3. Click "Run workflow" and select the branch to deploy from

## Maintaining Authentication During Deployments

The CI/CD pipeline is configured to maintain your JWT authentication setup:

1. The GitHub workflow passes the `SECRET_KEY` as an environment variable
2. Your tokens will remain valid across deployments
3. No need to regenerate tokens after a deployment

## Testing a Deployment

After a deployment completes, verify it worked:

```bash
# Check if the container is running
ssh root@164.92.69.88 "docker ps | grep crawl4ai-container"

# Test the API with your token
curl -H "Authorization: Bearer YOUR_TOKEN" https://s.dy.me/health
```

## Troubleshooting

If a deployment fails:

1. Check the GitHub Actions logs for errors
2. SSH into your server and check the Docker logs:
   ```bash
   ssh root@164.92.69.88 "docker logs crawl4ai-container"
   ```
3. Verify that all GitHub secrets are properly set
