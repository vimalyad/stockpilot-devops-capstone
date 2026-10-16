# AWS infrastructure — not deployed

This configuration defines a VPC, two public and two private subnets across two availability zones, EKS, two managed workers (maximum four), encrypted gp3 worker disks, EBS CSI and Pod Identity, Kubernetes secret encryption, API/audit logs, VPC flow logs and a restricted operator /32 API endpoint.

No AWS account credentials are available for this project session. A successful static check is not an AWS plan or deployment. Regional versions, quotas, access and prices must be checked before creating infrastructure.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Set operator_cidr to your current public IPv4 /32.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=stockpilot.tfplan
# Review the concrete plan and obtain authorization before spending.
terraform apply stockpilot.tfplan
aws eks update-kubeconfig --region us-east-1 --name vimal-stockpilot-capstone
kubectl apply -f ../k8s/namespace.yaml
kubectl apply -f ../k8s/storageclass-eks.yaml
# Create application secrets, then install Helm with postgres.storageClass=stockpilot-gp3.
```

The default uses one NAT gateway and private worker subnets. The single NAT is a deliberate demo cost compromise and an availability dependency; production would use one per availability zone. Setting `enable_nat_gateway=false` puts workers in public subnets with public IPs so image pulls work without a NAT. The private subnets remain defined. This alternative is for a brief controlled lab, not the production recommendation.

EKS, EC2 workers, NAT, public IPv4, EBS, logs and data transfer can incur charges. There is no automatic spending cap. Use a short session and capture evidence before teardown. Delete Ingress/load balancers, uninstall app and monitoring releases, and deliberately handle retained database PVCs/volumes. Then run `terraform destroy` and check AWS for remaining EBS volumes, load balancers and logs. The StorageClass uses Retain to protect data; those volumes require a separate explicit deletion decision.

EKS node group scaling is not automatically connected to pod HPA. HPA scales API pods within available capacity; install Cluster Autoscaler/Karpenter before expecting nodes to scale automatically. PostgreSQL and Redis are single-instance persistent demo services, not a high-availability database cluster.
