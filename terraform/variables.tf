variable "region" {
  type    = string
  default = "us-east-1"
}
variable "cluster_name" {
  type    = string
  default = "vimal-stockpilot-capstone"
}
variable "operator_cidr" {
  type        = string
  description = "Operator's current public IPv4 /32; required for API access."
  validation {
    condition     = can(cidrhost(var.operator_cidr, 0)) && endswith(var.operator_cidr, "/32")
    error_message = "Use a valid single IPv4 address with /32."
  }
}
variable "kubernetes_version" {
  type        = string
  default     = "1.35"
  description = "Confirm regional EKS support immediately before applying."
}
variable "node_type" {
  type    = string
  default = "t3.medium"
}
variable "enable_nat_gateway" {
  type        = bool
  default     = false
  description = "True: workers in private subnets through one billed NAT. False: demo workers in public subnets, no NAT bill."
}
