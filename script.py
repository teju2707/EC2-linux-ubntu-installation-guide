# Create comprehensive shell scripts for complete Kubernetes master node setup with kubeaudit
import os

# Main comprehensive setup script
main_script = """#!/bin/bash

# Complete Kubernetes Master Node Setup with kubeaudit
# Run as root user: sudo ./k8s-master-complete-setup.sh

set -e  # Exit on any error

echo "==============================================="
echo "    Kubernetes Master Node Complete Setup"
echo "==============================================="

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Phase 1: System Preparation
log_info "Phase 1: System Preparation"
echo "=============================="

log_info "Updating system packages..."
apt-get update && apt-get upgrade -y

log_info "Setting hostname to master-node..."
hostnamectl set-hostname master-node

log_info "Disabling swap permanently..."
swapoff -a
sed -i '/swap/d' /etc/fstab

log_info "Loading kernel modules..."
modprobe overlay
modprobe br_netfilter

# Create modules config
cat <<EOF > /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

log_info "Configuring sysctl parameters..."
cat <<EOF > /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sysctl --system
log_success "Phase 1 completed: System prepared"

# Phase 2: containerd Installation
log_info "Phase 2: containerd Installation"
echo "=================================="

log_info "Installing prerequisites..."
apt-get install -y apt-transport-https ca-certificates curl software-properties-common wget

cd /tmp

log_info "Downloading containerd..."
CONTAINERD_VERSION="1.7.18"
wget https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

log_info "Installing containerd..."
tar Cxzvf /usr/local containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

log_info "Downloading runc..."
RUNC_VERSION="1.1.12"
wget https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64
install -m 755 runc.amd64 /usr/local/sbin/runc

log_info "Installing CNI plugins..."
CNI_VERSION="1.5.1"
wget https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz
mkdir -p /opt/cni/bin
tar Cxzvf /opt/cni/bin cni-plugins-linux-amd64-v${CNI_VERSION}.tgz

log_info "Configuring containerd..."
mkdir -p /etc/containerd
/usr/local/bin/containerd config default > /etc/containerd/config.toml
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml

log_info "Creating containerd systemd service..."
curl -L https://raw.githubusercontent.com/containerd/containerd/main/containerd.service -o /etc/systemd/system/containerd.service

systemctl daemon-reload
systemctl enable --now containerd

# Verify containerd
if systemctl is-active --quiet containerd; then
    log_success "containerd is running"
else
    log_error "containerd failed to start"
    exit 1
fi

log_success "Phase 2 completed: containerd installed and configured"

# Phase 3: Kubernetes Installation
log_info "Phase 3: Kubernetes Components Installation"
echo "=============================================="

log_info "Adding Kubernetes repository..."
mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' > /etc/apt/sources.list.d/kubernetes.list

log_info "Installing kubeadm, kubelet, kubectl..."
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

log_success "Phase 3 completed: Kubernetes components installed"

# Phase 4: Cluster Initialization
log_info "Phase 4: Cluster Initialization"
echo "================================"

log_info "Initializing Kubernetes cluster..."
kubeadm init \\
  --pod-network-cidr=192.168.0.0/16 \\
  --cri-socket=unix:///run/containerd/containerd.sock \\
  --ignore-preflight-errors=NumCPU,Mem > /tmp/kubeadm-init.log

# Extract join command
grep -A 2 "kubeadm join" /tmp/kubeadm-init.log > /tmp/kubeadm-join-command.txt

log_info "Setting up kubectl for regular user..."
if [[ $SUDO_USER ]]; then
    USER_HOME="/home/$SUDO_USER"
    sudo -u $SUDO_USER mkdir -p $USER_HOME/.kube
    cp -i /etc/kubernetes/admin.conf $USER_HOME/.kube/config
    chown $SUDO_USER:$SUDO_USER $USER_HOME/.kube/config
else
    mkdir -p $HOME/.kube
    cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
fi

export KUBECONFIG=/etc/kubernetes/admin.conf

log_info "Installing Calico CNI..."
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.1/manifests/calico.yaml

log_success "Phase 4 completed: Cluster initialized"

# Phase 5: kubeaudit Installation
log_info "Phase 5: kubeaudit Security Scanner Installation"
echo "================================================="

log_info "Downloading kubeaudit..."
cd /tmp
KUBEAUDIT_VERSION="0.22.2"
wget https://github.com/Shopify/kubeaudit/releases/download/v${KUBEAUDIT_VERSION}/kubeaudit_${KUBEAUDIT_VERSION}_linux_amd64.tar.gz

log_info "Installing kubeaudit..."
tar -xzf kubeaudit_${KUBEAUDIT_VERSION}_linux_amd64.tar.gz
chmod +x kubeaudit
mv kubeaudit /usr/local/bin/

# Verify kubeaudit
kubeaudit version
log_success "Phase 5 completed: kubeaudit installed"

# Phase 6: Create Sample Files and Scripts
log_info "Phase 6: Creating Helper Scripts and Sample Files"
echo "=================================================="

# Create sample pod for testing
cat <<EOF > /home/${SUDO_USER:-root}/sample-pod.yml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx
    ports:
    - containerPort: 80
EOF

# Create kubeaudit helper script
cat <<'EOF' > /usr/local/bin/k8s-security-scan
#!/bin/bash
echo "Kubernetes Security Scanning with kubeaudit"
echo "==========================================="

if [ "$1" = "cluster" ]; then
    echo "Scanning entire cluster..."
    kubeaudit all
elif [ "$1" = "manifest" ] && [ -n "$2" ]; then
    echo "Scanning manifest file: $2"
    kubeaudit all -f "$2"
elif [ "$1" = "autofix" ] && [ -n "$2" ]; then
    echo "Auto-fixing manifest file: $2"
    kubeaudit autofix -f "$2" -o "fixed-$2"
    echo "Fixed file created: fixed-$2"
else
    echo "Usage:"
    echo "  k8s-security-scan cluster                 # Scan running cluster"
    echo "  k8s-security-scan manifest <file.yml>     # Scan manifest file"
    echo "  k8s-security-scan autofix <file.yml>      # Auto-fix manifest file"
fi
EOF

chmod +x /usr/local/bin/k8s-security-scan

log_success "Phase 6 completed: Helper scripts created"

# Phase 7: Final Verification
log_info "Phase 7: Final Verification"
echo "============================"

log_info "Waiting for cluster to be ready..."
sleep 30

export KUBECONFIG=/etc/kubernetes/admin.conf

log_info "Checking node status..."
kubectl get nodes

log_info "Checking system pods..."
kubectl get pods -n kube-system

log_info "Testing kubeaudit..."
kubeaudit version

# Display join command
log_success "=== CLUSTER SETUP COMPLETED ==="
echo ""
log_success "Join command for worker nodes:"
cat /tmp/kubeadm-join-command.txt
echo ""
log_success "Sample commands to try:"
echo "  kubectl get nodes"
echo "  kubectl get pods -A"
echo "  k8s-security-scan cluster"
echo "  k8s-security-scan manifest sample-pod.yml"
echo ""
log_success "Master node setup completed successfully!"
"""

# Worker node setup script
worker_script = """#!/bin/bash

# Kubernetes Worker Node Setup Script
# Run as root: sudo ./k8s-worker-setup.sh

set -e

echo "==============================================="
echo "    Kubernetes Worker Node Setup"
echo "==============================================="

# Colors for output
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_info "Phase 1: System Preparation"
apt-get update && apt-get upgrade -y
hostnamectl set-hostname worker-node
swapoff -a
sed -i '/swap/d' /etc/fstab

# Load kernel modules
modprobe overlay
modprobe br_netfilter

cat <<EOF > /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

# Configure sysctl
cat <<EOF > /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sysctl --system

log_info "Phase 2: containerd Installation"
apt-get install -y apt-transport-https ca-certificates curl software-properties-tools wget

cd /tmp

# Install containerd
CONTAINERD_VERSION="1.7.18"
wget https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz
tar Cxzvf /usr/local containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

# Install runc
RUNC_VERSION="1.1.12"
wget https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64
install -m 755 runc.amd64 /usr/local/sbin/runc

# Install CNI plugins
CNI_VERSION="1.5.1"
wget https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz
mkdir -p /opt/cni/bin
tar Cxzvf /opt/cni/bin cni-plugins-linux-amd64-v${CNI_VERSION}.tgz

# Configure containerd
mkdir -p /etc/containerd
/usr/local/bin/containerd config default > /etc/containerd/config.toml
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml

# Create systemd service
curl -L https://raw.githubusercontent.com/containerd/containerd/main/containerd.service -o /etc/systemd/system/containerd.service
systemctl daemon-reload
systemctl enable --now containerd

log_info "Phase 3: Kubernetes Components"
mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' > /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

log_success "Worker node prepared! Ready to join cluster."
echo ""
echo "To join this worker to the cluster, run the join command from master node:"
echo "Example: sudo kubeadm join <MASTER-IP>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH> --ignore-preflight-errors=NumCPU,Mem"
"""

# Verification script
verify_script = """#!/bin/bash

# Kubernetes Cluster Verification Script

echo "Kubernetes Cluster Health Check"
echo "==============================="

export KUBECONFIG=/etc/kubernetes/admin.conf

echo "1. Node Status:"
kubectl get nodes -o wide

echo ""
echo "2. System Pods Status:"
kubectl get pods -n kube-system

echo ""
echo "3. Cluster Information:"
kubectl cluster-info

echo ""
echo "4. kubeaudit Version:"
kubeaudit version

echo ""
echo "5. Container Runtime Status:"
systemctl status containerd --no-pager -l

echo ""
echo "6. Security Scan Sample:"
echo "Run: k8s-security-scan cluster"
echo "Run: k8s-security-scan manifest sample-pod.yml"
"""

# Write all scripts to files
scripts = {
    "k8s-master-complete-setup.sh": main_script,
    "k8s-worker-setup.sh": worker_script,
    "k8s-verify-cluster.sh": verify_script
}

for filename, content in scripts.items():
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Created: {filename}")

print("\nAll scripts created successfully!")