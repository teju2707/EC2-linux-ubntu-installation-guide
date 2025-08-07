#!/bin/bash

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
