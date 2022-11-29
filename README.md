# TI Edgeai Studio Evm Agent



## A) FETCHING IP ADDRESS OF DEVICE VIA UART TERMINAL FROM HOST SIDE

- First connect the UART cable to your PC; Open your terminal 
- Start minicom session on PC using: 
```
sudo minicom -D /dev/ttyUSBX -c
```
- In above command COM port can vary (/dev/ttyUSB),to confirm that check which all usb serial ports available: 
```
ls /dev/tty | grep USB 
```
![usb serial ports list output](/images/usb_serial_ports.png)
- It will be mostly ttyUSB2 but to confirm try opening multiple minicom sessions with different serial ports (ttyUSB0, ttyUSB1, ttyUSB2, ttyUSB3) and check if the boot logs are visible on power cycle or POR. 

- When getting boot logs ; you will get login option as shown in the diagram, give root as login id 
![tda4vm login](/images/tda4vm_login.png)

 -For additional reference check link :- (https://www.ti.com/lit/ug/spruj21c/spruj21c.pdf?ts=1669039866167&ref_url=https%253A%252F%252Fwww.google.com%252Fur ) **refer Section :- 2.3.1 Uart-Over-USB [J4] With LED for Status** 

- Now type command **ifconfig** to get the ip address, the highlighted one as shown in the figure below: 
![ifconfig output](/images/get_ip-address.png)

- Now you can ssh into the target using this ip address using CMD(via HOST PC):
```
ssh root@ip-address
```
## B) Downloading and getting device agent up and running on target EVM 

1. Download the evm agent repo tar file from gitlab into your pc from this link: (https://gitlab.ignitarium.in/ti-edgeai_studio/ti-edgeai-studio-evm-agent)

(Note: If a clone of above repo can be done on target EVM this will be the recommended option since change we make can easily be updated. If cloning skip steps 2 and 3 , always clone repo into /opt/edge_ai_apps/apps_python/ on target) 

2. Transfer above .tar into target to this location  /opt/edge_ai_apps/apps_python/ 

3. Extract the file in device using command :  tar –xvf /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main.tar.gz  (Note: Extract to /opt/edge_ai_apps/apps_python/ location) 

4. Apply patch onto gst_wrapper.py for enabling the inference pipeline using CMD:
```
patch /opt/edge_ai_apps/apps_python/gst_wrapper.py /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main/patch_folder/gst_wrapper_patch.txt 
```
5. Apply patch onto post_process.py for resolving sdk bug to enable the object_detection inference using CMD:
```
patch /opt/edge_ai_apps/apps_python/post_process.py /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main/patch_folder/post_process_patch.txt 
```
5. Navigate to the folder using CMD:
```
cd /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main/ 
```
6.  Run the following script to install dependencies.
```
./req_native.sh script
```
7. Go to src folder using CMD: 
```
cd /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main/src 
```
8. Execute device agent script using CMD: 
```
python3 device_agent.py  
```
- Note: Ensure you are inside folder /opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent-main/src before running device_agent.py
