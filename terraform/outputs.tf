output "cluster_name" { value = aws_eks_cluster.lab.name }
output "region" { value = var.region }
output "vpc_id" { value = aws_vpc.lab.id }
output "public_subnets" { value = aws_subnet.public[*].id }
output "private_subnets" { value = aws_subnet.private[*].id }
output "update_kubeconfig" { value = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.lab.name}" }
output "worker_network" { value = var.enable_nat_gateway ? "private subnets with single NAT" : "public subnets; demo cost mode" }
