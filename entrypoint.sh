Setup odoo in kube

1. Install docker : https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
2. Install Kube : https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
3. sudo swapoff -a
4. sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
5. sudo nano /etc/modules-load.d/containerd.conf
6. add to file :
	overlay
	br_netfilter
7. sudo modprobe overlay
8. sudo modprobe br_netfilter
9. sudo nano /etc/sysctl.d/kubernetes.conf
10. add to file: 
	net.bridge.bridge-nf-call-ip6tables = 1
	net.bridge.bridge-nf-call-iptables = 1
	net.ipv4.ip_forward = 1
11. sudo sysctl --system
12. sudo hostnamectl set-hostname master-node
13. sudo hostnamectl set-hostname worker01
14. sudo nano /etc/hosts
15. addo to file:
	ip master-node
	ip worker01
16. sudo nano /etc/default/kubelet
17. KUBELET_EXTRA_ARGS="--cgroup-driver=cgroupfs"
18. sudo systemctl daemon-reload && sudo systemctl restart kubelet
19. sudo nano /etc/docker/daemon.json
20. add to file:
	{
      "exec-opts": ["native.cgroupdriver=systemd"],
      "log-driver": "json-file",
      "log-opts": {"max-size": "100m"},
      "storage-driver": "overlay2"
    }
21. sudo systemctl daemon-reload && sudo systemctl restart docker
22. sudo nano /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
23. add to file:
	#Note: This dropin only works with kubeadm and kubelet v1.11+
	[Service]
	Environment="KUBELET_KUBECONFIG_ARGS=--bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --kubeconfig=/etc/kubernetes/kubelet.conf"
	Environment="KUBELET_CONFIG_ARGS=--config=/var/lib/kubelet/config.yaml"
	Environment="KUBELET_EXTRA_ARGS=--fail-swap-on=false"
	# This is a file that "kubeadm init" and "kubeadm join" generates at runtime, populating the KUBELET_KUBEADM_ARGS variable dynamically
	EnvironmentFile=-/var/lib/kubelet/kubeadm-flags.env
	# This is a file that the user can use for overrides of the kubelet args as a last resort. Preferably, the user should use
	# the .NodeRegistration.KubeletExtraArgs object in the configuration files instead. KUBELET_EXTRA_ARGS should be sourced from this file.
	EnvironmentFile=-/etc/default/kubelet
	ExecStart=
	ExecStart=/usr/local/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_CONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS
24. sudo kubeadm init --control-plane-endpoint=ip:6443 --pod-network-cidr=192.168.0.0/16
25. mkdir -p $HOME/.kube sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config sudo chown $(id -u):$(id -g) $HOME/.kube/config
26  kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
27. kubectl taint nodes --all node-role.kubernetes.io/control-plane-
28. sudo nano odoo.deployment.yaml
29. copy file odoo.deployment.yaml ke add to file
30. kubectl apply -f odoo.deployment.yaml
30. sudo nano db.deployment.yaml
31. copy file db.deployment.yaml ke add to file
32. kubectl apply -f db.deployment.yaml
