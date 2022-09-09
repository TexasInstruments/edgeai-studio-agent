#! /bin/sh

for I in /sys/class/video4linux/*
do
	if cat $I/name | grep "WEBCAM";
	then 
		echo $I
		break
	fi
	i=$(($i + 1))
done

		

