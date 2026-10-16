resource "aws_eks_cluster" "lab" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version
  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  encryption_config {
    resources = ["secrets"]
    provider { key_arn = aws_kms_key.eks.arn }
  }
  upgrade_policy { support_type = "STANDARD" }
  vpc_config {
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = [var.operator_cidr]
  }
  depends_on = [aws_iam_role_policy_attachment.cluster, aws_route_table_association.public]
}
resource "aws_launch_template" "node" {
  name_prefix = "${var.cluster_name}-"
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }
  tag_specifications {
    resource_type = "instance"
    tags          = { Project = "stockpilot-capstone", Session = "21", Name = var.cluster_name }
  }
  tag_specifications {
    resource_type = "volume"
    tags          = { Project = "stockpilot-capstone", Session = "21" }
  }
}
resource "aws_eks_node_group" "lab" {
  cluster_name    = aws_eks_cluster.lab.name
  node_group_name = "stockpilot-workers"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.enable_nat_gateway ? aws_subnet.private[*].id : aws_subnet.public[*].id
  ami_type        = "AL2023_x86_64_STANDARD"
  instance_types  = [var.node_type]
  capacity_type   = "ON_DEMAND"
  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 4
  }
  launch_template {
    id      = aws_launch_template.node.id
    version = aws_launch_template.node.latest_version
  }
  depends_on = [aws_iam_role_policy_attachment.node, aws_route_table_association.private, aws_route.private_nat]
}
resource "aws_eks_addon" "pod_identity" {
  cluster_name = aws_eks_cluster.lab.name
  addon_name   = "eks-pod-identity-agent"
  depends_on   = [aws_eks_node_group.lab]
}
resource "aws_eks_pod_identity_association" "storage" {
  cluster_name    = aws_eks_cluster.lab.name
  namespace       = "kube-system"
  service_account = "ebs-csi-controller-sa"
  role_arn        = aws_iam_role.storage.arn
  depends_on      = [aws_iam_role_policy_attachment.storage, aws_eks_addon.pod_identity]
}
resource "aws_eks_addon" "storage" {
  cluster_name = aws_eks_cluster.lab.name
  addon_name   = "aws-ebs-csi-driver"
  depends_on   = [aws_eks_pod_identity_association.storage]
}

resource "aws_kms_key" "eks" {
  description             = "StockPilot EKS secret encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}
