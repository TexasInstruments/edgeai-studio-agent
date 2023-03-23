# TI EdgeAI Studio Agent

TI EdgeAI Studio Agent is required to be started on a TI Analytics device to use
EdgeAI Studio with the device. To know more about EdgeAI Studio please visit
https://dev.ti.com/edgeaistudio


# Steps to Run

## A) Fetching IP Address of Device via UART Terminal

1. First connect the UART cable to your PC and Open your terminal

2. Start minicom session on PC using:

    `sudo minicom -D /dev/ttyUSBX -c on`

3. In above command COM port can vary (/dev/ttyUSB), to confirm that check which
all usb serial ports available:

    `ls /dev/tty | grep USB`

    ![usb serial ports list output](/images/usb_serial_ports.png)

    - It will be mostly ttyUSB2 but to confirm try opening multiple minicom
    sessions with different serial ports (ttyUSB0, ttyUSB1, ttyUSB2, ttyUSB3)
    and check if the boot logs are visible on power cycle or POR.

4. When getting boot logs ; you will get login option as shown in the diagram,
give root as login id

    ![tda4vm login](/images/tda4vm_login.png)

    -For additional reference check link :-
    (https://www.ti.com/lit/ug/spruj21c/spruj21c.pdf?ts=1669039866167&ref_url=https%253A%252F%252Fwww.google.com%252Fur )
    **refer Section :- 2.3.1 Uart-Over-USB [J4] With LED for Status**

5. Now type command **ifconfig** to get the ip address, the highlighted one as
shown in the figure below:

    ![ifconfig output](/images/get_ip-address.png)

6. Now you can ssh into the target using this ip address using CMD(via HOST PC):

    `ssh root@ip-address`

## B) Running device agent on target

1. Navigate to edgeai-studio-agent folder:

    `cd /opt/edgeai-studio-agent/src`

2. Execute device agent script:

    `python3 device_agent.py`

    - Note: Ensure you are inside folder /opt/edgeai-studio-agent/src before
    running device_agent.py
