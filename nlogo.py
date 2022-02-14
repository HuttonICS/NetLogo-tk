#!/usr/bin/python3
"""nlogo.py
This module contains classes for reading and working with a NetLogo model.
Run from the command line, it can be used to:

* Extract all the parameters from the model's GUI tab into a CSV file
  (This can then be used in a subsequent call to create an experiment)

  ./nlogo.py <nlogo file> param <file to save parameters to>

* Print a list of the experiments from the model's behaviour space

  ./nlogo.py <nlogo file> expt

* Split an experiment's settings into individual experiments

  ./nlogo.py <nlogo file> split <experiment name> <experiment XML file>

* Prepare a script to run all the split experiments with Sun Grid Engine

  ./nlogo.py <nlogo file> splitq <experiment name> <experiment XML file>
                                 <file to save SGE submission script to>

* Prepare a Monte Carlo sample of parameter space

  ./nlogo.py <nlogo file> monte <parameter file> <tick number to stop at>
                                <number of samples> <experiment XML file>

  Note: if the number of samples is large, the XML library used by NetLogo
  to read in the experiment file can cause out-of-memory and garbage
  collection errors, or result in the model taking a long time to run. Use
  number of samples > 10000 with caution.

  The created experiment file automatically collects data from plot pens
  and monitors each step.

* Prepare a Monte Carlo sample of parameter space with a shell script to
  run all the options with Sun Grid Engine

  ./nlogo.py <nlogo file> montq <parameter file> <tick number to stop at>
                                <number of samples> <experiment XML file>
                                <file to save SGE submission script to>

  You can then submit the jobs with qsub <SGE submission script>

A typical workflow would be to run this with param and then montq, before
qsubbing the submission script. Once you've extracted the results you want
from the outputs, you could then use, for example bruteABC.py to analyse
the results.

Other potentially useful tools (for future implementation)

* Extract and collate outputs from NetLogo experiments in an XML file

* Automatically split up large sample sizes for monte and montq into
  chunks of, say, 20000 runs at a time. (DONE)

* Creata a qsub script to run a BehaviorSpace experiment in parallel (DONE)

* Parse code and do things with it, like extracting an ontology, or UML
  diagrams

* Automatically add a licence (e.g. GNU GPL) section to the Info tab

* Check progress with experiment runs by looking for output files
"""
# Copyright (C) 2018  The James Hutton Institute & University of Edinburgh
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public Licence as published by
# the Free Software Foundation, either version 3 of the Licence, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public Licence for more details.
#
# You should have received a copy of the GNU General Public Licence
# along with this program.  If not, see <https://www.gnu.org/licences/>.
__version__ = "0.4"
__author__ = "Gary Polhill"

# Imports
import io
import os
import re
import sys
import math
import random as rnd
import xml.etree.ElementTree as xml

# Classes

class Widget:
    """
    The Widget class is a top-level class for all of the items that you can
    put on the GUI tab of a NetLogo model.
    """
    type = "<<UNDEF>>"
    def __init__(self, type, left, top, right, bottom, display, parameter,
                 output, info):
        self.type = type
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.display = display
        self.isParameter = parameter
        self.isOutput = output
        self.isInfo = info

    @staticmethod
    def read(fp):
        """
        Reads the widgets section from a NetLogo file, returning an array
        of widgets read
        """
        typestr = fp.readline()
        widgets = []
        while(typestr[0:-1] != "@#$#@#$#@"):
            typestr = typestr.strip()

            if typestr == GraphicsWindow.type:
                widgets.append(GraphicsWindow.read(fp))
            elif typestr == Button.type:
                widgets.append(Button.read(fp))
            elif typestr == Plot.type:
                widgets.append(Plot.read(fp))
            elif typestr == TextBox.type:
                widgets.append(TextBox.read(fp))
            elif typestr == Switch.type:
                widgets.append(Switch.read(fp))
            elif typestr == Chooser.type:
                widgets.append(Chooser.read(fp))
            elif typestr == Slider.type:
                widgets.append(Slider.read(fp))
            elif typestr == Monitor.type:
                widgets.append(Monitor.read(fp))
            elif typestr == OutputArea.type:
                widgets.append(OutputArea.read(fp))
            elif typestr == InputBox.type:
                widgets.append(InputBox.read(fp))
            else:
                sys.stderr.write("Unrecognized widget type: %s\n"%(typestr))
                while(typestr.strip() != ""):
                    typestr = fp.readline()

            typestr = fp.readline()
            if typestr == "":
                break
            if typestr.strip() == '':
                typestr = fp.readline()

        return widgets


class GraphicsWindow(Widget):
    """
    The GraphicsWindow class is a subclass of Widget that contains the space
    """
    type = "GRAPHICS-WINDOW"
    def __init__(self, left, top, right, bottom, patch_size, font_size, x_wrap,
                 y_wrap, min_pxcor, max_pxcor, min_pycor, max_pycor, update_mode,
                 show_ticks, tick_label, frame_rate):
        Widget.__init__(self, GraphicsWindow.type, left, top, right, bottom, "",
                        False, True, False)
        self.patchSize = patch_size
        self.fontSize = font_size
        self.xWrap = x_wrap
        self.yWrap = y_wrap
        self.minPXCor = min_pxcor
        self.maxPXCor = max_pxcor
        self.minPYCor = min_pycor
        self.maxPYCor = max_pycor
        self.updateMode = update_mode
        self.showTicks = show_ticks
        self.tickLabel = tick_label
        self.frameRate = frame_rate

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        res1 = fp.readline()
        res2 = fp.readline()
        patch_size = float(fp.readline())
        res3 = fp.readline()
        font_size = int(fp.readline())
        res4 = fp.readline()
        res5 = fp.readline()
        res6 = fp.readline()
        res7 = fp.readline()
        x_wrap = fp.readline().strip() == "1"
        y_wrap = fp.readline().strip() == "1"
        res8 = fp.readline()
        min_pxcor = int(fp.readline())
        max_pxcor = int(fp.readline())
        min_pycor = int(fp.readline())
        max_pycor = int(fp.readline())
        update_mode = int(fp.readline())
        res9 = fp.readline()
        show_ticks = fp.readline().strip() == "1"
        tick_label = fp.readline().strip()
        frame_rate = float(fp.readline())

        return GraphicsWindow(left, top, right, bottom, patch_size, font_size,
                              x_wrap, y_wrap, min_pxcor, max_pxcor, min_pycor,
                              max_pycor, update_mode, show_ticks, tick_label,
                              frame_rate)


class Button(Widget):
    """
    The Button class is a subclass of Widget containing a button
    """
    type = "BUTTON"
    def __init__(self, left, top, right, bottom, display, code, forever,
                 button_type, action_key, always_enable):
        Widget.__init__(self, Button.type, left, top, right, bottom, display,
                        False, False, False)
        self.code = code
        self.forever = forever
        self.buttonType = button_type
        self.actionKey = action_key
        self.alwaysEnable = always_enable

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        code = fp.readline().strip()
        forever = (fp.readline().strip() == "T")
        res1 = fp.readline()
        res2 = fp.readline()
        button_type = fp.readline().strip()
        res3 = fp.readline()
        action_key = fp.readline().strip()
        res4 = fp.readline()
        res5 = fp.readline()
        always_enable = (int(fp.readline()) == 1)

        return Button(left, top, right, bottom, display, code, forever,
                      button_type, action_key, always_enable)

class Parameter(Widget):
    """
    The Parameter class is an abstract subclass of Widget for all parameter widgets.
    Subclasses include Slider, Switch, Chooser and InputBox
    """
    def __init__(self, type, left, top, right, bottom, display):
        Widget.__init__(self, type, left, top, right, bottom, display, True, False, False)
        self.varname = '<<UNDEF>>'
        self.default = 'NA'
        self.value = 'NA'
        self.datatype = 'string'

    def variable(self):
        return self.varname

    def settingStr(self):
        return str(self.value)

    def datatypeStr(self):
        return str(self.datatype)

    def setValue(self, value):
        self.value = value

class Output(Widget):
    """
    The Output class is an abstract subclass of Widget containing some output.
    Subclasses include Plot, Monitor and OutputArea
    """
    def __init__(self, type, left, top, right, bottom, display):
        Widget.__init__(self, type, left, top, right, bottom, display, False, True, False)

class Info(Widget):
    """
    The Info class is an abstract subclass of Widget containing information.
    TextBox is the subclass of Info.
    """
    def __init__(self, type, left, top, right, bottom, display):
        Widget.__init__(self, type, left, top, right, bottom, display, False, False, True)

class Plot(Output):
    """
    Plot widget
    """
    type = "PLOT"
    def __init__(self, left, top, right, bottom, display, xaxis, yaxis, xmin,
                 xmax, ymin, ymax, autoplot_on, legend_on, code1, code2):
        Output.__init__(self, Plot.type, left, top, right, bottom, display)
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.xmin = xmin
        self.ymin = ymin
        self.ymax = ymax
        self.autoplotOn = autoplot_on
        self.legendOn = legend_on
        self.code1 = code1
        self.code2 = code2
        self.pens = {}

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        xaxis = fp.readline().strip()
        yaxis = fp.readline().strip()
        xmin = float(fp.readline())
        xmax = float(fp.readline())
        ymin = float(fp.readline())
        ymax = float(fp.readline())
        autoplot_on = (fp.readline().strip() == "true")
        legend_on = (fp.readline().strip() == "true")
        codes = (fp.readline().strip().split('" "'))

        plot = Plot(left, right, top, bottom, display, xaxis, yaxis,
                    xmin, xmax, ymin, ymax, autoplot_on, legend_on,
                    codes[0][1:-1], codes[1][0:-2])
        if fp.readline().strip() == "PENS":
            penstr = fp.readline().strip()
            while penstr != '':
                plot.addPen(Pen.parse(penstr))
                penstr = fp.readline().strip()

        return plot

    def addPen(self, pen):
        self.pens[pen.display] = pen

    def getPens(self):
        return self.pens.values()

class Pen:
    """
    The Pen class contains data for each pen of a Plot
    """
    def __init__(self, display, interval, mode, colour, in_legend, setup_code,
                 update_code):
        self.display = display
        self.interval = interval
        self.mode = mode
        self.colour = colour
        self.inLegend = in_legend
        self.setupCode = setup_code
        self.updateCode = update_code

    @staticmethod
    def parse(penstr):
        words = penstr.split()
        display = words[0]
        i = 1
        while not display.endswith('"'):
            display = display + " " + words[i]
            i = i + 1
        interval = float(words[i])
        mode = int(words[i + 1])
        colour = int(words[i + 2])
        in_legend = (words[i + 3] == "true")
        setup_code = words[i + 4]
        i = i + 5
        while setup_code.endswith('\\"') or not setup_code.endswith('"'):
            setup_code = setup_code + " " + words[i]
            i = i + 1
        update_code = " ".join(words[i:])
        return Pen(display, interval, mode, colour, in_legend, setup_code, update_code)

class TextBox(Info):
    """
    TextBox is an Info containing some text
    """
    type = "TEXTBOX"
    def __init__(self, left, top, right, bottom, display, font_size, colour,
                 transparent):
        Info.__init__(self, TextBox.type, left, top, right, bottom, display)
        self.fontSize = font_size
        self.colour = colour
        self.transparent = transparent

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        font_size = int(fp.readline())
        colour = float(fp.readline())
        txt = fp.readline().strip()
        transparent = (txt == 'true' or txt == '1' or txt == 'T')
        return TextBox(left, top, right, bottom, display, font_size, colour,
                       transparent)

class Switch(Parameter):
    """
    Switch Parameter widget
    """
    type = "SWITCH"
    def __init__(self, left, top, right, bottom, display, varname, on):
        Parameter.__init__(self, Switch.type, left, top, right, bottom, display)
        self.varname = varname
        self.isSwitchedOn = on
        self.value = self.isSwitchedOn
        self.datatype = 'boolean'

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        varname = fp.readline().strip()
        txt = fp.readline().strip()
        on = (txt == '0')
        res1 = fp.readline()
        res2 = fp.readline()
        return Switch(left, top, right, bottom, display, varname, on)

class Chooser(Parameter):
    """
    Chooser Parameter widget
    """
    type = "CHOOSER"
    def __init__(self, left, top, right, bottom, display, varname, choices,
                 selection):
        Parameter.__init__(self, Chooser.type, left, top, right, bottom, display)
        self.varname = varname
        self.choices = choices
        self.selection = selection
        self.value = self.selection
        self.datatype = 'integer'

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        varname = fp.readline().strip()
        txt = fp.readline().strip()
        words = txt.split()
        choices = []
        choices.append(words[0])
        i = 1
        j = 0
        while i < len(words):
            while choices[j].startswith('"') and not choices[j].endswith('"'):
                choices[j] = choices[j] + " " + words[i]
                i = i + 1
            if i >= len(words):
                break
            choices.append(words[i])
            j = j + 1
            i = i + 1
        selection = int(fp.readline())
        return Chooser(left, top, right, bottom, display, varname, choices,
                       selection)

    def getSelectionStr(self):
        return self.choices[self.selection]


class Slider(Parameter):
    """
    Slider Parameter widget
    """
    type = "SLIDER"
    def __init__(self, left, top, right, bottom, display, varname, min, max,
                 default, step, units, orientation):
        Parameter.__init__(self, Slider.type, left, top, right, bottom, display)
        self.varname = varname
        self.minimum = min
        self.maximum = max
        self.default = default
        self.step = step
        self.units = units
        self.isHorizontal = (orientation == "HORIZONTAL")
        self.value = self.default
        self.datatype = 'numeric'

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        varname = fp.readline().strip()
        min = fp.readline().strip()
        max = fp.readline().strip()
        default = float(fp.readline())
        step = fp.readline().strip()
        res1 = fp.readline()
        units = fp.readline().strip()
        orientation = fp.readline().strip()
        return Slider(left, top, right, bottom, display, varname, min, max,
                      default, step, units, orientation)

class Monitor(Output):
    """
    Monitor Output Widget
    """
    type = "MONITOR"
    def __init__(self, left, top, right, bottom, display, source, precision,
                 font_size):
        Output.__init__(self, Monitor.type, left, top, right, bottom, display)
        self.source = source
        self.precision = precision
        self.fontSize = font_size

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        display = fp.readline().strip()
        source = fp.readline().strip().replace("\\\"", "\"")
        precision = int(fp.readline())
        res1 = fp.readline()
        font_size = int(fp.readline())
        return Monitor(left, top, right, bottom, display, source, precision,
                       font_size)

class OutputArea(Output):
    """
    OutputArea Output widget
    """
    type = "OUTPUT"
    def __init__(self, left, top, right, bottom, font_size):
        Output.__init__(self, OutputArea.type, left, top, right, bottom, "")

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        font_size = int(fp.readline())
        display = ""
        return Output(left, top, right, bottom, font_size, display)

class InputBox(Parameter):
    """
    InputBox Parameter widget
    """
    type = "INPUTBOX"
    def __init__(self, left, top, right, bottom, varname, value, multiline,
                 datatype):
        Parameter.__init__(self, InputBox.type, left, top, right, bottom, "")
        self.varname = varname
        self.value = value
        self.isMultiline = multiline
        self.isNumeric = (datatype == "Number")
        self.isString = (datatype == "String")
        self.isCommand = (datatype == "String (command)")
        self.isReporter = (datatype == "String (reporter)")
        self.isColour = (datatype == "Color")
        if self.isNumeric or self.isColour:
            self.datatype = 'numeric'
        if self.isString:
            self.value = "\"" + value + "\""

    @staticmethod
    def read(fp):
        left = int(fp.readline())
        top = int(fp.readline())
        right = int(fp.readline())
        bottom = int(fp.readline())
        varname = fp.readline().strip()
        value = fp.readline().strip()
        txt = fp.readline().strip()
        multiline = (txt == 'true' or txt == '1' or txt == 'T')
        res1 = fp.readline()
        datatype = fp.readline().strip()
        return InputBox(left, top, right, bottom, varname, value, multiline,
                        datatype)

class BahaviorSpaceXMLError(Exception):
    """
    Exception class for when there is unexpected content in the BehaviorSpace
    section of a NetLogo file.
    """
    def __init__(self, file, expected, found):
        self.file = file
        self.expected = expected
        self.found = found

    def __str__(self):
        return "BehaviorSpace XML format error in file %s: expected \"%s\", found \"%s\""%(self.file, self.expected, self.found)

class SteppedValue:
    """
    A class containing data from a stepped value parameter exploration in a
    BehaviorSpace
    """
    def __init__(self, variable, first, step, last):
        if step < 0.0 and first < last:
            raise ValueError("In BehaviorSpace, variable \"%s\" has negative step %f with start %f < stop %f"%(variable, step, first, last))
        elif step > 0.0 and first > last:
            raise ValueError("In BehaviorSpace, variable \"%s\" has step %f with start %f > stop %f"%(variable, step, first, last))
        elif step == 0.0 and first != last:
            raise ValueError("In BehaviorSpace, variable \"%s\" has step 0.0 with start %f != stop %f"%(variable, step, first, last))
        self.variable = variable
        self.first = first
        self.step = step
        self.last = last
        self.values = []
        self.values.append(first)
        while self.values[-1] < self.last:
            self.values.append(self.step + self.values[-1])

    def getValues(self):
        return self.values

    def getNValues(self):
        return len(self.values)

    @staticmethod
    def fromXML(xml, file_name):
        if xml.tag != "steppedValueSet":
            raise BehaviorSpaceXMLError(file_name, "steppedValueSet", xml.tag)
        return SteppedValue(xml.get("variable"), float(xml.get("first")),
                            float(xml.get("step")), float(xml.get("last")))

class EnumeratedValue:
    """
    A class containing data from an enumerated value parameter exploration
    in a BehaviorSpace
    """
    def __init__(self, variable, values):
        self.variable = variable
        if isinstance(values, list):
            self.values = values
        else:
            self.values = []
            self.values.append(values)

    def getValues(self):
        return self.values

    def getNValues(self):
        return len(self.values)

    @staticmethod
    def fromXML(xml, file_name):
        if xml.tag != "enumeratedValueSet":
            raise BehaviorSpaceXMLError(file_name, "enumeratedValueSet", xml.tag)

        variable = xml.get("variable")
        values = []
        for value in xml:
            if value.tag != "value":
                raise BehaviorSpaceXMLError(file_name, "value", value.tag)
            values.append(value.get("value"))

        return EnumeratedValue(variable, values)

class Experiment:
    """
    Class containing data from a single BehaviorSpace experiment
    """
    def __init__(self, name, setup, go, final, time_limit, exit_condition,
                 metrics, stepped_values = [], enumerated_values = [],
                 repetitions = 1, sequential_run_order = True,
                 run_metrics_every_step = True, results = "."):
        self.name = name
        self.setup = setup
        self.go = go
        self.final = final
        self.timeLimit = time_limit
        self.exitCondition = exit_condition
        self.metrics = metrics
        self.steppedValueSet = stepped_values
        self.enumeratedValueSet = enumerated_values
        self.repetitions = int(repetitions)
        self.sequentialRunOrder = sequential_run_order
        self.runMetricsEveryStep = run_metrics_every_step
        self.results = results # Directory where any output should be

    def getNRuns(self):
        runs = self.repetitions
        for param in self.steppedValueSet:
            runs *= param.getNValues()
        for param in self.enumeratedValueSet:
            runs *= param.getNValues()
        return runs

    def uniqueSettings(self):
        """
        Return an array of all the runs in this experiment with unique
        parameter settings
        """
        experiments = []

        counters = {}
        maxes = {}
        for param in self.steppedValueSet:
            counters[param.variable] = 0
            maxes[param.variable] = param.getNValues()
        for param in self.enumeratedValueSet:
            counters[param.variable] = 0
            maxes[param.variable] = param.getNValues()

        done = False
        i = 0
        n = self.getNRuns() / self.repetitions
        while not done:
            new_name = "%s-%0*d" % (self.name, (1 + int(math.log10(n))), i)
            i += 1 # i starts at 0 for consistency with monte/montq
            enumerated_values = []

            for param in self.steppedValueSet:
                # N.B. adding this single value to enumerated_values is
                # deliberate; the new experiment will have no stepped values
                enumerated_values.append(EnumeratedValue(param.variable,
                    param.getValues()[counters[param.variable]]))
            for param in self.enumeratedValueSet:
                enumerated_values.append(EnumeratedValue(param.variable,
                    param.getValues()[counters[param.variable]]))

            experiments.append(Experiment(new_name, self.setup, self.go,
                self.final, self.timeLimit, self.exitCondition, self.metrics,
                [], enumerated_values, self.repetitions, self.sequentialRunOrder,
                self.runMetricsEveryStep))

            for var in counters.keys():
                counters[var] += 1
                if counters[var] == maxes[var]:
                    counters[var] = 0
                else:
                    break

            done = all([v == 0 for v in counters.values()])

        return experiments

    @staticmethod
    def fromXMLString(str, file_name):
        """
        Parse a full <experiments>...</experiments> XML string into an
        array of Experiments, which is returned
        """
        experiments = []
        if str == None or str.strip() == "":
            return []
        xmlstr = xml.XML(str)
        if xmlstr.tag != "experiments":
            raise BehaviorSpaceXMLError(file_name, "experiments", xmlstr.tag)
        for exp in xmlstr:
            if exp.tag != "experiment":
                raise BehaviorSpaceXMLError(file_name, "experiment", exp.tag)
            repetitions = 1
            sequential_run_order = True
            run_metrics_every_step = True
            name = None
            for attr in exp.keys():
                if attr == "name":
                    name = exp.get(attr)
                elif attr == "repetitions":
                    repetitions = exp.get(attr)
                elif attr == "sequentialRunOrder":
                    sequential_run_order = (exp.get(attr) == "true")
                elif attr == "runMetricsEveryStep":
                    run_metrics_every_step = (exp.get(attr) == "true")
                else:
                    raise BehaviorSpaceXMLError(file_name,
                        "name|repetitions|sequentialRunOrder|runMetricsEveryStep",
                        attr)
            if name == None:
                raise BehaviorSpaceXMLError(file_name, "name",
                                            "no \"name\" attribute for experiment")
            setup = ""
            go = ""
            final = ""
            time_limit = None
            exit_condition = None
            metrics = []
            stepped_values = []
            enumerated_values = []

            for elem in exp:
                if elem.tag == "setup":
                    setup = elem.text
                elif elem.tag == "go":
                    go = elem.text
                elif elem.tag == "final":
                    final = elem.text
                elif elem.tag == "timeLimit":
                    time_limit = float(elem.get("steps"))
                    if time_limit == None:
                        raise BehaviorSpaceXML(file_name, "steps",
                                               "no \"steps\" attribute for timeLimit")
                elif elem.tag == "exitCondition":
                    exit_condition = elem.text
                elif elem.tag == "metric":
                    metrics.append(elem.text)
                elif elem.tag == "steppedValueSet":
                    stepped_values.append(SteppedValue.fromXML(elem, file_name))
                elif elem.tag == "enumeratedValueSet":
                    enumerated_values.append(EnumeratedValue.fromXML(elem, file_name))
                else:
                    raise BehaviorSpaceXML(file_name, "experiment sub-element", elem.tag)

            experiments.append(Experiment(name, setup, go, final, time_limit,
                               exit_condition, metrics, stepped_values,
                               enumerated_values, repetitions,
                               sequential_run_order, run_metrics_every_step))
        return experiments

    @staticmethod
    def fromWidgets(widgets, name, stop):
        """
        Create an Experiment object from the parameter and output widgets on
        the GUI. Current parameter settings on the GUI will be used as the
        parameter values, and outputs used as metrics.
        """
        setup = ""
        go = ""
        outputs = []
        params = []

        for w in widgets:
            if isinstance(w, Button):
                if(w.display == "setup" or w.code == "setup"):
                    setup = w.code.replace("\\n", "\n")
                elif(w.display == "go" or w.code == "go"):
                    go = w.code.replace("\\n", "\n")
            elif isinstance(w, Output) and not isinstance(w, OutputArea):
                outputs.append(w)
            elif isinstance(w, Parameter):
                params.append(w)

        expt = None
        if isinstance(stop, int):
            expt = Experiment(name, setup, go, "", stop, None, [])
        else:
            expt = Experiment(name, setup, go, "", None, str(stop), [])
        expt = expt.withParameterSettings(params)
        for w in outputs:
            expt.addMetric(w)

        return expt

    def withParameterSettings(self, param):
        """
        Return a new Experiment the same as this one, but using the parameter
        settings contained in the param array
        """
        new_enum_set = []
        for p in param:
            if isinstance(p, Parameter):
                valuearr = []
                if p.datatypeStr() == 'string' and not p.settingStr().startswith('"') and not p.settingStr().startswith('&quot;'):
                    valuearr.append('"' + p.settingStr() + '"')
                else:
                    valuearr.append(p.settingStr())
                new_enum_set.append(EnumeratedValue(p.variable(), valuearr))
            else:
                new_enum_set.append(EnumeratedValue(p, param[p]))
        return Experiment(self.name, self.setup, self.go, self.final, self.timeLimit,
                          self.exitCondition, self.metrics, [], new_enum_set,
                          self.repetitions, self.sequentialRunOrder,
                          self.runMetricsEveryStep)

    def withSamples(self, samples):
        """
        Create an experiment from this one, changing the parameter settings to
        be set randomly from the array of samples passed as argument
        """
        param = {}
        for s in samples:
            name = s.param.variable()
            value = s.sample()
            param[name] = value
        return self.withParameterSettings(param)

    def withNSamples(self, samples, n, final_save = False):
        """
        Create an array of experiments from this one, changing the parameter
        settings such that each is set randomly from the array of samples
        passed as argument
        """
        expts = []
        for i in range(0, n):
            new_name = "%s-%0*d" % (self.name, (1 + int(math.log10(n))), i)
            expt = self.withSamples(samples)
            expt.rename(new_name)
            if final_save:
                expt.finallySaveParamMetricsExpt()
            expts.append(expt)
        return expts

    @staticmethod
    def writeExperimentHeader(fp):
        """
        Write the XML header to save the experiments as an XML file
        """
        fp.write(u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        fp.write(u"<!DOCTYPE experiments SYSTEM \"behaviorspace.dtd\">\n")
        fp.write(u"<experiments>\n")

    @staticmethod
    def writeExperimentFooter(fp):
        """
        Write the XML footer to save the experiments as an XML file
        """
        fp.write(u"</experiments>\n")

    @staticmethod
    def writeExperiments(file_name, expts, max_size = 10000, max_batch = 5000):
        """
        Save an array of experiments as an XML file
        """
        if len(expts) <= max_size:
            try:
                fp = io.open(file_name, "w")
            except IOError as e:
                sys.stderr.write("Error creating file %s: %s\n"%(file_name, e.strerror))
                return False

            Experiment.writeExperimentHeader(fp)

            for expt in expts:
                expt.writeExperimentDetails(fp)

            Experiment.writeExperimentFooter(fp)
            fp.close()

        else:
            n_batch = math.ceil(len(expts) / max_batch)
            for batch in range(0, n_batch):
                batch_str = str.format("{:0%dd}"%(1 + int(math.log10(float(n_batch)))), batch)
                batch_file = file_name[0:(len(file_name) - 4)] + "-" + batch_str + ".xml"

                try:
                    fp = io.open(batch_file, "w")
                except IOError as e:
                    sys.stderr.write("Error creating file %s: %s\n"%(batch_file, e.strerror))
                    return False

                Experiment.writeExperimentHeader(fp)

                batch_min = batch * max_batch
                batch_max = batch_min + max_batch
                if batch_max > len(expts):
                    batch_max = len(expts)

                for expt in expts[batch_min:batch_max]:
                    expt.writeExperimentDetails(fp)

                Experiment.writeExperimentFooter(fp)
                fp.close()

        return True

    def writeExperimentDetails(self, fp):
        """
        Write the XML encoding of this Experiment to the file pointer fp
        """
        fp.write(u"  <experiment name=\"%s\" repetitions=\"%d\" sequentialRunOrder=\"%s\" runMetricsEveryStep=\"%s\">\n"
                 %(self.name, self.repetitions,
                   "true" if self.sequentialRunOrder else "false",
                   "true" if self.runMetricsEveryStep else "false"))
        if self.setup != "":
            fp.write(u"    <setup>%s</setup>\n" % self.escape(self.setup))
        if self.go != "":
            fp.write(u"    <go>%s</go>\n" % self.escape(self.go))
        if self.final != "":
            fp.write(u"    <final>\n%s\n    </final>\n" % self.escape(self.final))
        if self.timeLimit != None:
            fp.write(u"    <timeLimit steps=\"%d\"/>\n" % math.ceil(self.timeLimit))
        if self.exitCondition != None:
            fp.write(u"    <exitCondition>%s</exitCondition>\n" % self.escape(self.exitCondition))
        for m in self.metrics:
            fp.write(u"    <metric>%s</metric>\n" % self.escape(m))

        for v in self.steppedValueSet:
            fp.write(u"    <steppedValueSet variable=\"%s\" first=\"%f\" step=\"%f\" last=\"%f\"/>\n"
                     %(v.variable, v.first, v.step, v.last))

        for v in self.enumeratedValueSet:
            fp.write(u"    <enumeratedValueSet variable=\"%s\">\n" % v.variable)
            for w in v.values:
                fp.write(u"      <value value=\"%s\"/>\n" % str(w).replace('"', '&quot;'))
            fp.write(u"    </enumeratedValueSet>\n")

        fp.write(u"  </experiment>\n")

    def escape(self, str):
        """
        Escape ampersands, quotes and inequalities when writing XML data
        """
        return str.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

    def writeExperiment(self, file_name):
        try:
            fp = io.open(file_name, "w")
        except IOError as e:
            sys.stderr.write("Error creating file %s: %s\n"%(file_name, e.strerror))
            return False

        Experiment.writeExperimentHeader(fp)

        self.writeExperimentDetails(fp)

        Experiment.writeExperimentFooter(fp)
        fp.close()

        return True

    def rename(self, new_name):
        self.name = str(new_name)

    def setReps(self, reps):
        self.repetitions = int(reps)

    def setSequentialRunOrder(self, seq):
        self.sequentialRunOrder = bool(seq)

    def setRunMetricsEveryStep(self, run):
        self.runMetricsEveryStep = bool(run)

    def setSetup(self, setup):
        if isinstance(setup, Button):
            self.setup = setup.code
        else:
            self.setup = str(setup)

    def addProgress(self):
        f = "behaviorspace-experiment-name \"-\" behaviorspace-run-number \"-prog.txt\""
        if self.results != ".":
            f = "\"{dir}/\" " + f
        f = "(word " + f + ")"
        self.setup += "\nfile-open {f}\nfile-print (word \"0 / {s}: \" date-and-time)\nfile-close".format(
            f = f, s = self.timeLimit)
        self.go += "\nfile-open {f}\nfile-print (word ticks \" / {s}: \" date-and-time)\nfile-close".format(
            f = f, s = self.timeLimit)

    def setGo(self, go):
        if isinstance(go, Button):
            self.go = go.code
        else:
            self.go = str(go)

    def setFinal(self, final):
        self.final = str(final)

    def finallySaveParamMetrics(self, file_name):
        paramStr = ""
        wordStr = ""
        for v in self.steppedValueSet:
            paramStr = paramStr + v.variable + ","
            wordStr = wordStr + v.variable + " \",\" "
        for v in self.enumeratedValueSet:
            paramStr = paramStr + v.variable + ","
            wordStr = wordStr + v.variable + " \",\" "
        for m in self.metrics:
            paramStr = paramStr + m.replace(",", ".").replace('"', ".") + ","
            wordStr = wordStr + "(" + m + ") \",\" "
        if self.results != ".":
            file_name = self.results + "/" + file_name
        self.final = '''
            ifelse file-exists? "{file}" [
                file-open "{file}"
            ] [
                file-open "{file}"
                file-print "{param}"
            ]
            file-print (word {word})
            file-close
        '''.format(file = file_name, param = paramStr[:-1], word = wordStr[:-5])

    def finallySaveParamMetricsExpt(self):
        self.finallySaveParamMetrics(self.name + ".csv")

    def setTimeLimit(self, limit):
        self.timeLimit = float(limit)

    def setExitCondition(self, exitCond):
        self.exitCondition = str(exitCond)

    def clearMetrics(self):
        self.metrics = []

    def addMetric(self, metric):
        if isinstance(metric, Monitor):
            self.metrics.append(metric.source)
        elif isinstance(metric, Plot):
            for p in metric.getPens():
                self.addMetric(p)
        elif isinstance(metric, Pen):
            code = metric.updateCode
            if code.startswith('"'):
                code = code[1:-1].replace('\\"', '"')
            if code.startswith('plot '):
                code = code[5:]
            if not code.startswith('histogram '):
                self.metrics.append(code)
        elif not isinstance(metric, Output):
            self.metrics.append(str(metric))

    def clearSteppedValueSet(self):
        self.steppedValueSet = []

    def addSteppedValue(self, variable, first, step, last):
        self.steppedValueSet.append(SteppedValue(str(variable), float(first), float(step), float(last)))

    def clearEnumeratedValueSet(self):
        self.enumeratedValueSet = []

    def addEnumeratedValue(self, variable, values):
        self.enumeratedValueSet.append(EnumeratedValue(str(variable), values))


class NetlogoModel:
    def __init__(self, code, widgets, info, shapes, version, preview, sd,
                 behav, hubnet, link_shapes, settings, deltatick):
        self.code = code
        self.widgets = widgets
        self.info = info
        self.shapes = shapes
        self.version = version
        self.preview = preview
        self.sd = sd
        self.behav = behav
        self.hubnet = hubnet
        self.linkShapes = link_shapes
        self.settings = settings
        self.deltatick = deltatick
        self.params = {}
        self.expts = {}

    @staticmethod
    def readSection(fp):
        section = ""
        for line in fp:
            if line[0:-1] == "@#$#@#$#@":
                break
            section = section + line
        return section

    @staticmethod
    def read(file_name):
        try:
            fp = io.open(file_name)
        except IOError as e:
            sys.stderr.write("Error opening file %s: %s\n"%(file_name, e.strerror))
            return False

        code = NetlogoModel.readSection(fp)

        widgets = Widget.read(fp)

        info = NetlogoModel.readSection(fp)

        shapes = NetlogoModel.readSection(fp)

        version = NetlogoModel.readSection(fp)
        version = version[0:-1]

        preview = NetlogoModel.readSection(fp)

        sd = NetlogoModel.readSection(fp)

        behav = Experiment.fromXMLString(NetlogoModel.readSection(fp), file_name)

        hubnet = NetlogoModel.readSection(fp)

        link_shapes = NetlogoModel.readSection(fp)

        settings = NetlogoModel.readSection(fp)

        deltatick = NetlogoModel.readSection(fp)

        return NetlogoModel(code, widgets, info, shapes, version, preview,
                            sd, behav, hubnet, link_shapes, settings, deltatick)

    def getParameters(self):
        if len(self.params) == 0:
            for w in self.widgets:
                if(isinstance(w, Parameter)):
                    self.params[w.variable()] = w
        return self.params

    def getExperiments(self):
        if len(self.expts) == 0 and len(self.behav) != 0:
            for b in self.behav:
                self.expts[b.name] = b
        return self.expts

    def writeParameters(self, file_name):
        try:
            fp = io.open(file_name, "w")
        except IOError as e:
            sys.stderr.write("Error creating file %s: %s\n"%(file_name, e.strerror))

        fp.write(u"parameter,type,setting,minimum,maximum\n")

        param = self.getParameters()

        for key in sorted(param.keys()):
            fp.write(u"%s,%s,%s"%(key, param[key].datatypeStr(), param[key].settingStr()))
            if param[key].datatypeStr() == 'numeric' or param[key].datatypeStr() == 'integer':
                if isinstance(param[key], Slider):
                    fp.write(u",%s,%s\n"%(str(param[key].minimum), str(param[key].maximum)))
                elif isinstance(param[key], Chooser):
                    fp.write(u",0,%d\n"%(len(param[key].choices) - 1))
                else:
                    fp.write(u",%s,%s\n"%(param[key].settingStr(), param[key].settingStr()))
            elif param[key].datatypeStr() == 'boolean':
                fp.write(u",true,false\n")
            else:
                fp.write(u",NA,NA\n")

        fp.close()

    def printExperiments(self):
        if len(self.behav) == 0:
            print("There are no experiments")
        else:
            print("Experiments:")
            for expt in self.behav:
                n = expt.getNRuns()

                print("\t" + expt.name + " (" + str(expt.getNRuns()) + (" run)" if n == 1 else " runs)") )

    def splitExperiment(self, name, file, max_size = 10000, max_batch = 5000):
        self.getExperiments()
        if len(self.behav) == 0:
            print("There are no experiments")
            return 0
        elif name not in self.expts:
            print("There is no experiment named " + name)
            return 0
        else:
            expt = self.expts[name]
            splitted = expt.uniqueSettings()
            Experiment.writeExperiments(file, splitted, max_size, max_batch)
            print("Written " + str(len(splitted)) + " experiments to \"" + file + "\"")
            return len(splitted)

class Sample:
    def __init__(self, param, datatype, setting, minimum, maximum):
        self.param = param
        self.setting = setting
        self.datatype = datatype
        self.minimum = minimum
        self.maximum = maximum

    @staticmethod
    def read(file_name, params):
        try:
            fp = io.open(file_name)
        except IOError as e:
            sys.stderr.write("Error opening file %s: %s\n"%(file_name, e.strerror))
            return False

        header = fp.readline().strip()

        samples = []
        for line in fp:
            line = line.strip()
            words = line.split(",")
            if words[0] in params:
                param = params[words[0]]
                samples.append(Sample(param, words[1], words[2], words[3], words[4]))
            else:
                sys.stderr.write("Warning: parameter %s ignored\n" % words[0])

        fp.close()
        return samples

    def sample(self):
        if self.minimum == "NA" or self.maximum == "NA":
            return self.setting
        elif self.minimum == self.maximum:
            if isinstance(self.param, Chooser):
                if self.maximum.isnumeric():
                    return self.param.choices[int(self.maximum)]
                else:
                    return self.maximum
            else:
                return self.minimum
        else:
            if self.datatype == "integer":
                rint = rnd.randint(int(self.minimum), int(self.maximum))
                if isinstance(self.param, Chooser):
                    return self.param.choices[rint]
                else:
                    return rint
            elif self.datatype == "numeric":
                return rnd.uniform(float(self.minimum), float(self.maximum))
            elif self.datatype == "boolean":
                return (rnd.random() < 0.5)
            else:
                if isinstance(self.param, Chooser):
                    if self.setting.isnumeric():
                        return self.param.choices[int(self.setting)]
                    else:
                        return self.setting
                else:
                    return self.setting

    def setSample(self):
        self.param.setValue(self.sample())

class Batch:
    def __init__(self, java, netlogo, headless, model, xml, expt, nruns, dir,
                 batch, cores, gigaram, concur = 0, threads = 1, outstream = "",
                 errstream = "", zip = True, delay = 1, time = 86400, nanny = "",
                 project = "", wait = 0, jobname = ""):
        self.java = java
        self.netlogo = netlogo
        self.headless = headless
        self.model = model
        self.dir = dir
        self.name = jobname if jobname != "" else xml[:-4]
        if batch <= 1:
            self.xml = xml
            self.batchzeros = 0
        else:
            self.xml = self.name + "-$BATCH_NO.xml"
            self.batchzeros = 1 + int(math.log10((nruns / batch) - 1))
            if self.dir == ".":
                self.dir = "$BATCH_NO"
            else:
                self.dir = "{dir}/{xml}-$BATCH_NO".format(dir = dir, xml = self.name)
        self.expt = expt
        self.nruns = nruns
        self.nrunzeros = 1 if nruns <= 1 else 1 + int(math.log10(nruns - 1))
        self.batch = batch
        self.cores = cores
        self.threads = threads
        self.gigaram = gigaram
        self.concur = concur
        if concur > nruns:
            self.concur = self.nruns
        self.outstream = outstream
        self.errstream = errstream
        self.zip = zip
        self.delay = delay
        self.time = time
        self.nanny = nanny
        self.project = ""
        self.wait = wait

    @staticmethod
    def defaultBatch(model, xml, expt, nruns, batch, dir, cores = 2, gigaram = 4,
        concur = 0, threads = 1, outstream = "/dev/null", errstream = "/dev/null",
        zip = False, delay = 0, time = 86400, nanny = "",
        java = '/mnt/apps/java/jdk-14.0.2', netlogo = '/mnt/apps/netlogo-6.2.0',
        headless = '/mnt/apps/netlogo-6.2.0/netlogo-headless-1cpu-4g.sh'):

        java_home = os.getenv("JAVA_HOME", java)
        netlogo_home = os.getenv("NETLOGO_HOME", netlogo)
        netlogo_invoke = os.getenv("NETLOGO_INVOKE", headless)
        return Batch(java_home, netlogo_home, netlogo_invoke, model, xml, expt,
            nruns, dir, batch, cores, gigaram, concur, threads, outstream,
            errstream, zip, delay, time, nanny)

    def saveSGE(self, file_name):
        try:
            fp = io.open(file_name, "w")
        except IOError as e:
            sys.stderr.write("Error creating file %s: %s\n"%(file_name, e.strerror))
        fp.write(u'''#!/bin/sh
#$ -cwd
#$ -t 1-{nrun}
#$ -pe smp {svr_cores}
#$ -N {name}
#$ -l h_cpu={time}
'''.format(nrun = self.nruns, svr_cores = self.cores,
            name = self.name, time = self.time))
        if self.concur != 0:
            fp.write(u"#$ -tc {concur}\n".format(concur = self.concur))
        if self.outstream != "":
            fp.write(u"#$ -o {out}\n".format(out = self.outstream))
        if self.errstream != "":
            if self.errstream == self.outstream:
                fp.write(u"#$ -j y\n")
            else:
                fp.write(u"#$ -e {err}\n".format(err = self.errstream))
        if self.project != "":
            fp.write(u"#$ -P {proj}\n".format(proj = self.project))

        if self.gigaram != 0:
            fp.write(u"#$ -l h_vmem={mem}m\n".format(mem = int(self.gigaram * 1024 / self.cores)))
        fp.write(u"printf -v JOB_ID \"%0{size}d\" $(expr $SGE_TASK_ID - 1)\n".format(
            size = self.nrunzeros
        ))
        if self.batch > 1:
            fp.write(u"printf -v BATCH_NO \"%0{batchsize}d\" $(expr $SGE_TASK_ID / {maxbatch})\n".format(
                batchsize = self.batchzeros,
                maxbatch = self.batch
            ))
        if self.nanny == "":
            self.saveCommon(fp)
        else:
            self.saveCommon(fp, self.nanny)
        fp.close()
        os.chmod(file_name, 0o755)

    def saveSLURM(self, file_name):
        try:
            fp = io.open(file_name, "w")
        except IOError as e:
            sys.stderr.write("Error creating file %s: %s\n"%(file_name, e.strerror))
        fp.write(u"#!/bin/sh\n")
        if self.wait == 0:
            fp.write(u"#SBATCH --begin=now\n")
        else:
            fp.write(u"#SBATCH --begin=now+{wait}\n".format(wait = self.wait))
        fp.write(u"#SBATCH --cpus-per-task={cores}\n#SBATCH --job-name={name}\n".format(
            cores = self.cores, name = self.name))
        if self.time != 0:
            fp.write(u"#SBATCH --time={time}\n".format(time = math.ceil(self.time / 60)))
        if self.outstream != "":
            fp.write(u"#SBATCH --output={out}\n".format(out = self.outstream))
        if self.errstream != "":
            fp.write(u"#SBATCH --error={err}\n".format(err = self.errstream))
        if self.concur != 0:
            fp.write(u"#SBATCH --array=1-{nrun}%{concur}\n".format(
                nrun = self.nruns, concur = self.concur)
            )
        else:
            fp.write(u"#SBATCH --array=1-{nrun}\n".format(nrun = self.nruns))
        if self.project != "":
            fp.write(u"#SBATCH --wckey={proj}".format(proh = self.project))
        if self.gigaram != 0:
            fp.write(u"#SBATCH --mem-per-cpu={mem}\n".format(
                mem = int(self.gigaram * 1024 / self.cores))
            )
        fp.write(u"printf -v JOB_ID \"%0{size}d\" $(expr $SLURM_ARRAY_TASK_ID - 1)\n".format(
            size = self.nrunzeros
        ))

        if self.batch > 1:
            fp.write(u"printf -v BATCH_NO \"%0{batchsize}d\" $(expr $SLURM_ARRAY_TASK_ID / {maxbatch})\n".format(
                batchsize = self.batchzeros, maxbatch = self.batch
            ))

        if self.nanny == "":
            self.saveCommon(fp, "srun")
        else:
            self.saveCommon(fp, "srun " + self.nanny)
        fp.close()
        os.chmod(file_name, 0o755)

    def saveCommon(self, fp, cmd = ""):
        if self.delay != 0:
            fp.write(u"sleep $((RANDOM % {delay}))\n".format(delay = self.delay))
        fp.write(u"mdir=\"`pwd`\"\n")
        fp.write(u"xdir=\"`pwd`\"\n")
        if self.dir != '.':
            fp.write(u"rdir=\"`pwd`/{dir}\"\n".format(dir = self.dir))
            fp.write(u"test -d \"$rdir\" || mkdir \"$rdir\"\n")
        else:
            fp.write(u"rdir=\"`pwd`\"\n")

        fp.write(u'''
xml="$xdir/{xml}"
export JAVA_HOME="{java_home}"
cd "{nlogo_home}"
xpt="{expt}-$JOB_ID"
out="$rdir/{expt}-$JOB_ID.out"
csv="$rdir/{expt}-$JOB_ID-table.csv"
{cmd} "{nlogo_invoke}" --model "$mdir/{model}" --setup-file "$xml" --experiment "$xpt" --threads {nlogo_threads} --table "$csv" > "$out" 2>&1
'''.format(size = self.nrunzeros, xml = self.xml, java_home = self.java,
            nlogo_home = self.netlogo, expt = self.expt, cmd = cmd,
            nlogo_invoke = self.headless, model = self.model,
            nlogo_threads = self.threads))
        if self.zip:
            fp.write(u"test -e \"$out\" && gzip \"$out\"\n")
            fp.write(u"test -e \"$csv\" && gzip \"$csv\"\n")

class Options:
    def __init__(self, args):
        self.defaults()
        i = 1
        while i < len(args) and args[i][0] == "-":
            if args[i] == "--batch-max" or args[i] == "-b":
                i += 1
                self.max_batch = int(args[i])
                if self.batch_size > self.max_batch:
                    self.batch_size = self.max_batch
            elif args[i] == "--batch-size" or args[i] == "-B":
                i += 1
                self.batch_size = int(args[i])
            elif args[i] == "--dir" or args[i] == "-d":
                i += 1
                self.dir = args[i]
            elif args[i] == "--error" or args[i] == "-e":
                i += 1
                self.err = args[i]
            elif args[i] == "--find-netlogo" or args[i] == "-f":
                i += 1
                self.nlogo_home = args[i]
            elif args[i] == "--gibibytes" or args[i] == "-g":
                i += 1
                self.gigaram = int(args[i])
            elif args[i] == "--no-limit-ram" or args[i] == "-G":
                self.limit_ram = False
            elif args[i] == "--help" or args[i] == "-h":
                self.help()
            elif args[i] == "--headless" or args[i] == "-H":
                self.nlogo_invoke = "netlogo-headless.sh"
            elif args[i] == "--invoke-netlogo" or args[i] == "-i":
                i += 1
                self.nlogo_invoke = args[i]
            elif args[i] == "--java" or args[i] == "-j":
                i += 1
                self.java = args[i]
            elif args[i] == "--job-name" or args[i] == "-J":
                i += 1
                self.jobname = args[i]
            elif args[i] == "--kill-days" or args[i] == "-k":
                i += 1
                self.days = float(args[i])
            elif args[i] == "--limit-concurrent" or args[i] == "-l":
                i += 1
                self.concur = int(args[i])
            elif args[i] == "--nanny" or args[i] == "-n":
                i += 1
                self.nanny = True
            elif args[i] == "--no-nanny" or args[i] == "-N":
                i += 1
                self.nanny = False
            elif args[i] == "--output" or args[i] == "-o":
                i += 1
                self.out = args[i]
            elif args[i] == "--project" or args[i] == "-p":
                i += 1
                self.project = args[i]
            elif args[i] == "--sleep-random" or args[i] == "-s":
                i += 1
                self.delay = int(args[i])
            elif args[i] == "--SGE":
                self.cluster = "SGE"
            elif args[i] == "--SLURM":
                self.cluster = "SLURM"
            elif args[i] == "--threads" or args[i] == "-t":
                i += 1
                self.threads = int(args[i])
            elif args[i] == "--threads-gc" or args[i] == "-T":
                i += 1
                self.gc = int(args[i])
            elif args[i] == "--version" or args[i] == "-v":
                i += 1
                self.nlogov = args[i]
            elif args[i] == "--wait" or args[i] == "-w":
                i += 1
                self.wait = int(args[i])
            elif args[i] == "--mc-expt" or args[i] == "-x":
                i += 1
                self.name = args[i]
            elif args[i] == "--no-zip" or args[i] == "-z":
                self.zip = False
            elif args[i] == "--zip" or args[i] == "-Z":
                self.zip = True
            elif args[i] == "--":
                i += 1
                break
            else:
                sys.stderr.write("Option \"{opt}\" not recognized\n".format(opt = args[i]))
                sys.exit(1)
            i += 1
        self.model = args[i]
        i += 1
        self.cmd = args[i]
        i += 1
        self.cmd_args = []
        while i < len(args):
            self.cmd_args.append(args[i])
            i += 1
        if self.cmd == "param":
            if len(self.cmd_args) == 0:
                self.cmd_args.append("{stem}.csv".format(stem = self.model[0:-6]))
        elif self.cmd == "expts":
            None
        elif self.cmd == "split":
            if len(self.cmd_args) == 1:
                self.cmd_args.append("{stem}.xml".format(stem = self.cmd_args[0]))
            elif len(self.cmd_args) == 0:
                sys.stderr.write("split needs at least one argument\n")
                sys.exit(1)
        elif self.cmd == "splitq":
            if len(self.cmd_args) == 1:
                self.cmd_args.append("{stem}.xml".format(stem = self.cmd_args[0]))
                self.cmd_args.append("{stem}.sh".format(stem = self.cmd_args[0]))
            elif len(self.cmd_args) == 2:
                self.cmd_args.append("{stem}.sh".format(stem = self.cmd_args[1][0:-4]))
            elif len(self.cmd_args) == 0:
                sys.stderr.write("splitq needs at least one argument\n")
                sys.exit(1)
        elif self.cmd == "monte":
            if len(self.cmd_args) == 3:
                self.cmd_args.append("{stem}.xml".format(stem = self.cmd_args[0][0:-4]))
            elif len(self.cmd_args) < 3:
                sys.stderr.write("monte needs at least three arguments\n")
                sys.exit(1)
        elif self.cmd == "montq":
            if len(self.cmd_args) == 3:
                self.cmd_args.append("{stem}.xml".format(stem = self.cmd_args[0][0:-4]))
                self.cmd_args.append("{stem}.sh".format(stem = self.cmd_args[0][0:-4]))
            elif len(self.cmd_args) == 4:
                self.cmd_args.append("{stem}.sh".format(stem = self.cmd_args[3][0:-4]))
            elif len(self.cmd_args) < 3:
                sys.stderr.write("montq needs at least three arguments\n")
                sys.exit(1)
        else:
            sys.stderr.write("Command \"{cmd}\" not recognized\n".format(cmd = self.cmd))
            sys.exit(1)

    @staticmethod
    def help():
        print('''Usage: [options] {cmd} <NetLogo model> <command> <command arguments...>
    options (mostly relevant only for commands creating scripts):

    --batch-max/-b <n>: maximum number of experiments to save in one XML file;
        the XML parser used in some versions of NetLogo can slow down
        significantly if this is more than 10000 (the default) or so. The
        script and experiment files will be split up into batches of size
        batch-size.
    --batch-size/-B <n>: if batch-max exceeded, experiments to save per XML
        file (should be less than or equal to batch-max, obvs.)
    --dir/-d <dir>: directory to save results to. If you're making lots of runs,
        this can be a good way of keeping things tidy in your top-level model
        directory.
    --error/-e <file>: file to save job submission script error stream to
        (output and error from the NetLogo command will be saved elsewhere)
    --find-netlogo/-f <dir>: where to find NetLogo
    --gibibytes/-g <n>: amount of RAM expected to be needed to run the model
        (adjusts the invocation script used and hard memory limits in the job
        submission script; use --no-limit-ram if you don't want the latter)
    --no-limit-ram/-G: don't use --gibibytes to limit the RAM in the job
        submission script
    --headless/-H: use the default netlogo-headless.sh to invoke NetLogo
    --help/-h: print this message and exit
    --invoke-netlogo/-i <exe>: use the specified NetLogo invocation script
    --java/-j <dir>: where to find the JAVA Virtual Machine (dir/bin/java)
    --job-name/-J <name>: identifier to use for the job's name on the cluster
        (defaults to the name of the experiment file)
    --kill-days/-k <n>: if the run isn't finished in n days, kill it; use 0
        to let it run indefinitely
    --limit-concurrent/-l <n>: limit the number of concurrent runs on the
        cluster; can be useful if this will be a long-running job and you want
        to submit other stuff while this is running
    --nanny/-n: use the 'childminder' program to monitor the model runs; see
        https://github.com/garypolhill/nanny
    --no-nanny/-N: don't use the 'childminder' program
    --output/-o <file>: file to save job submission script output stream to
        (output and error from the NetLogo command will still be saved)
    --project/-p <project>: project to charge (in the script); in SGE this
        sets the -P option in the job submission script; in SLURM the --wckey
    --sleep-random/-s <n>: each run should sleep random max n seconds before
        starting; this can be a good idea to stop hundreds of processes trying
        to access the same files at the same time
    --SGE: create a Sun Grid Engine submission script
    --SLURM: create a SLURM submission script (the default)
    --threads/-t <n>: use n threads in each simulation run for running the
        model; recommend 1 (the default), but this will be passed in the
        --threads option to NetLogo and affects the number of cores that will
        be requested for the run (with --threads-gc)
    --threads-gc/-T <n>: use n garbage collection threads (>= 2)
    --version/-v <version>: NetLogo version to use (e.g. 6.2.1)
    --wait/-w <n>: (SLURM only) queue n seconds from sbatch submission
    --mc-expt/-x <name>: experiment name stem to use for monte and montq
        commands
    --no-zip/-z: don't gzip the output file and table CSV file after the
        NetLogo run has finished
    --zip/-Z: do gzip the output file and table CSV file after the NetLogo run
        has finished (and save space)

    If you're not using The James Hutton Institute's agent-based modelling
    cluster, you will probably need to specify --find-netlogo and --java,
    with --headless given to use the default NetLogo headless invocation
    script or --invoke-netlogo to use one of your own. --gibibytes, --nanny,
    --project, --threads-gc and --version will then probably not do anything
    useful. On most clusters, you will want to muck around with the command
    line options to Java to adjust memory and the number of garbage collection
    threads.

    environment variables:

    +   JAVA_HOME: non-default JVM location to use
    +   NETLOGO_HOME: where to find NetLogo
    +   NETLOGO_INVOKE: full path to script to use to invoke NetLogo

    where <command> is one of:

    +   param [<CSV file>]

        Create a CSV file of all the model's parameters (one per row), with
        columns for parameter name, data type, current setting, minimum and
        maximum. If the CSV file is not given, the model name will be used
        to generate it.

    +   expts

        Print the list of names of experiments in the model file

    +   split <experiment name> [<XML file>]

        Take each of the unique parameter settings in the experiment with
        the given name, and create an experiment XML in which each setting
        has its own entry. If the XML file is not given, the experiment name
        will be used to generate it.

    +   splitq <experiment name> [<XML file> [<job submission script>]]

        As per the split command, but also create a job submission shell
        script in the named file allowing each unique parameter setting to be
        run in parallel on a computing cluster. If the XML file is not given,
        the experiment name is used to generate it and the job submission
        script; if the job submission script is not given, the XML file is
        used to generate it.

    +   monte <parameter CSV> <stop step> <n samples> [<XML file>]

        Create an experiment from the NetLogo file in which each of the
        parameters in the parameter CSV file (which you can create with the
        param command) is sampled at random between the specified minimum and
        maximum value (the current setting column is ignored), saving the
        result of the specific number of such samples to the XML file. If the
        XML file is not given the parameter CSV is used to generate it.

    +   montq <parameter CSV> <stop step> <n samples> [<XML file> [<script>]]

        As per the monte command, but then also write a job submission shell
        script in the named file allowing each of the parameter samples to be
        run in parallel on a computing cluster. If the XML file is not given,
        the parameter CSV is used to generate it and the script; if the script
        is not given, the XML file is used to generate it.

To submit the scripts created by splitq and montq, use qsub <script> on Sun
Grid Engine, or sbatch <script> on SLURM. On Hutton machines, if you haven't
used --project to specify in the submission script which account to accumulate
the CPU cycles in, you'll need to do this on the command line with qsub -P
<project> <script> on SGE, or sbatch --wckey=<project> <script> with SLURM.
'''.format(cmd = sys.argv[0]))
        sys.exit(0)

    def args(self):
        return self.cmd_args

    def makeBatch(self, xml, expt, nruns, batch):
        passram = 0
        if self.limit_ram:
            passram = self.gigaram
        self.batch = Batch(self.java, self.nlogoHome(), self.invokePath(), self.model,
                        xml, expt, nruns, self.dir, batch, self.cores(), passram,
                        concur = self.concur, threads = self.threads,
                        outstream = self.out, errstream = self.err, zip = self.zip,
                        delay = self.delay, time = int(self.days * 86400),
                        nanny = self.getNanny(), project = self.project,
                        wait = self.wait, jobname = self.jobname)

    @staticmethod
    def cmpver(v1, v2):
        tv1 = v1.split(".")
        tv2 = v2.split(".")
        maxi = min(len(tv1), len(tv2))
        for i in range(maxi):
            if tv1[i].isnumeric() and tv2[i].isnumeric():
                nv1 = int(tv1[i])
                nv2 = int(tv2[i])
                if nv1 < nv2:
                    return -1
                elif nv1 > nv2:
                    return 1
            else:
                if tv1[i] < tv2[i]:
                    return -1
                elif tv1[i] > tv2[i]:
                    return 1
        if len(tv1) < len(tv2):
            return -1
        elif len(tv1) > len(tv2):
            return 1
        else:
            return 0

    def defaults(self):
        self.cluster = "SLURM"
        self.gigaram = 4
        self.dir = "."
        self.concur = 0
        self.threads = 1
        self.gc = 3
        self.out = "/dev/null"
        self.err = "/dev/null"
        self.zip = False
        self.delay = 0
        self.days = 1
        self.nanny = False
        self.java = os.getenv("JAVA_HOME", "/mnt/apps/java/jdk-17.0.1")
        self.nlogo_home_dir = "/mnt/apps/netlogo"
        self.nlogov = "6.2.1"
        self.project = ""
        self.max_batch = 10000
        self.batch_size = 5000
        self.name = "x"
        self.wait = 0
        self.nlogo_home = ""
        self.nlogo_invoke = ""
        self.limit_ram = True
        self.jobname = ""

    def cores(self):
        return self.threads + self.gc

    def nlogoHome(self):
        if self.nlogo_home != "":
            return self.nlogo_home
        return os.getenv("NETLOGO_HOME", "{dir}-{ver}".format(
            dir = self.nlogo_home_dir, ver = self.nlogov))

    def invokeScript(self):
        if self.nlogo_invoke != "":
            return self.nlogo_invoke
        elif Options.cmpver(self.nlogov, "6.2.1") < 0:
            return "netlogo-headless-{cores}cpu-{gig}g.sh".format(
                cores = self.cores(), gig = self.gigaram)
        else:
            return "netlogo-headless-{gc}gc-{gig}Gi.sh".format(
                gc = self.gc, gig = self.gigaram)

    def invokePath(self):
        return os.getenv("NETLOGO_INVOKE", "{home}/{script}".format(
            home = self.nlogoHome(), script = self.invokeScript()))

    def getNanny(self):
        if self.nanny:
            return os.getenv("NANNY", "/mnt/apps/nanny/childminder")
        else:
            return ""

    def saveScript(self, filename):
        if self.cluster == "SLURM":
            self.batch.saveSLURM(filename)
        elif self.cluster == "SGE":
            self.batch.saveSGE(filename)
        else:
            sys.stderr.write("Cluster format \"{fmt}\" not recognized\n".format(
                fmt = self.cluster))

    def runCmd(self, script):
        if self.cluster == "SLURM":
            if self.project == "":
                return "sbatch --wckey=<project> {sh}".format(sh = script)
            else:
                return "sbatch {sh}".format(sh = script)
        elif self.cluster == "SGE":
            if self.project == "":
                return "qsub -P <project> {sh}".format(sh = script)
            else:
                return "qsub {sh}".format(sh = script)
        else:
            return script

if __name__ == "__main__":
    opts = Options(sys.argv)

    model = NetlogoModel.read(opts.model)
    if(model == False):
        sys.exit(1)
    print("Read \"{nlogo}\"".format(nlogo = opts.model))

    args = opts.args()

    if opts.cmd == 'param':
        model.writeParameters(args[0])
        print("Parameters written to \"{param}\"".format(param = args[0]))
    elif opts.cmd == 'expts':
        model.printExperiments()
    elif opts.cmd == 'split' or opts.cmd == 'splitq':
        nexpts = model.splitExperiment(args[0], args[1], opts.max_batch, opts.batch_size)
        if opts.cmd == 'splitq' and nexpts > 0:
            opts.makeBatch(args[1], args[0], nexpts, math.ceil(nexpts / opts.batch_size))
            opts.saveScript(args[2])
            print("Job submission script written to \"{sh}\"".format(sh = args[2]))
            print("Submit the script with \"{sub}\"".format(sub = opts.runCmd(args[2])))
    elif opts.cmd == 'monte' or opts.cmd == 'montq':
        samples = Sample.read(args[0], model.getParameters())
        expt = Experiment.fromWidgets(model.widgets, opts.name, int(args[1]))
        expts = expt.withNSamples(samples, int(args[2]), True)
        Experiment.writeExperiments(args[3], expts, opts.max_batch, opts.batch_size)
        print("Experiments written to \"{xml}\"".format(xml = args[3]))
        if opts.cmd == 'montq':
            opts.makeBatch(args[3], opts.name, int(args[2]), math.ceil(int(args[2]) / opts.batch_size))
            opts.saveScript(args[4])
            print("Job submission script written to \"{sh}\"".format(sh = args[4]))
            print("Submit the script with \"{sub}\"".format(sub = opts.runCmd(args[4])))

    sys.exit(0)
