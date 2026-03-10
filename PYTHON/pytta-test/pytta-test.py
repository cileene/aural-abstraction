#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Room Parameters.

Demonstration of how to use the new RoomParameters class.

@author: João Vitor Gutkoski Paes.
"""
import pytta


# myMonoIR = pytta.load("SOME_SAVED_SIGNALOBJ_WITH_IR.hdf5")
myMonoIR = pytta.read_wav("dales_site1_1way_mono.wav")


room = pytta.RoomAnalysis(myMonoIR, nthOct=3, minFreq=50., maxFreq=16e3)


print()
print("Parameters from impulse response are:")
print("\n", room.parameters, "\n")
print("Access directly by RoomAnalysis().PNAME")
print("Or view it in a bar plot by RoomAnalysis().plot_PNAME")
print("where PNAME is the name of the desired parameter, as shown above.")
print()
print(f"{room.T20=}")


fig = room.plot_EDT()
fig.show()

fig2 = room.plot_T20()
fig2.show()

fig3 = room.plot_T30()
fig3.show()

fig4 = room.plot_C80()
fig4.show()

fig5 = room.plot_D50()
fig5.show()

fig6 = room.plot_Ts()
fig6.show()