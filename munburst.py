#!/usr/bin/python
import treelib
import sys
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
#import xml.etree.ElementTree as ET
from lxml import etree as ET
import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.transforms as transforms
import textwrap
__version__ = "0.2"

WEDGE_COLOR     = '0.92'
CIRCLE_COLOR    = '#ee8d18'
COMPLETE_COLOR   = '#9CDCFF'
SELECTED_COLOR  = '#57D5FF'

last_id = 0
def draw_node(node, tree, center, radius, width, level, angle_from, angle_to, ax):
    texlen, textw = wrap_text(node.tag)
    if level == 0:
        fs  = scale_fontsize(texlen, 2*width, ax)
        w = Circle(center, radius=width, facecolor=CIRCLE_COLOR, edgecolor='k',picker=5, label=node.identifier)
        wp = Circle(center, radius=width*(node.value/100.0), facecolor=COMPLETE_COLOR,label=node.identifier)
        ax.text(center[0],center[1], textw, horizontalalignment='center', verticalalignment='center', fontsize=fs)
    else:
        w = Wedge(center, radius, angle_from, angle_to, width, facecolor=WEDGE_COLOR, ec='k',picker=5,label=node.identifier )
        wp = Wedge(center, radius, angle_from, angle_to, width*(node.value/100.0), facecolor=COMPLETE_COLOR,label=node.identifier )
        angle_t = (angle_to + angle_from)/2
        th = np.pi*angle_t/180
        if angle_t > 90 and angle_t < 270: 
            angle_t -=180
        t_x = center[0] +(radius - width/2)*np.cos(th)
        t_y = center[1] +(radius - width/2)*np.sin(th)

        fs  = scale_fontsize(texlen, width, ax)
        ax.text(t_x,t_y, textw, rotation=angle_t,horizontalalignment='center', verticalalignment='center', fontsize=fs, label=node.identifier)

    ax.add_artist(w)
    ax.add_artist(wp)

    valsum = 0
    for n in node.fpointer:
        valsum += tree.get_node(n).fraction

    arc_ang = angle_to - angle_from
    radius += width
    level +=1
    for n in node.fpointer:
        child = tree.get_node(n)
        af = angle_from 
        at = angle_from + child.fraction*arc_ang/valsum
        draw_node(child,tree, center,radius, width, level, af,at, ax)
        angle_from = at

def scale_fontsize(textlen, width,ax):
    ratio = 0.75 #font dependent
    
    inc = ax.figure.get_size_inches()
    inc = min(inc[0],inc[1])  # approximate!
      
    trans = ax.transData.transform([(0,1),(1,0)])-ax.transData.transform((0,0))
    pixs = trans[0,1] # should be square anyway

    dpi = pixs/inc # approximate!
    fs = width*pixs /(textlen*ratio * dpi/72.0)
    return np.round(fs)


def wrap_text(text):
    l = len(text)/2
    spaces =  [i for i, ltr in enumerate(text) if ltr == ' ']
    if len(spaces) == 0:
        return len(text),text
    s = map(lambda x: np.abs(l-x),spaces)
    m = min(s)

    split = spaces[s.index(m)]
    tw = textwrap.wrap(text, split,break_long_words=False)
    return max(split,len(text)-split), '\n'.join(tw)


def tree_depth(tree,node):
    childs = tree.get_node(node).fpointer
    if childs is None or len(childs) == 0:
        return 1
    else:
        return 1+max(map(lambda x: tree_depth(tree,x), childs))
    

def readGSP(filepath):
    global last_id
    xmltree = ET.parse(filepath)
    p = xmltree.getroot()
    #TODO header?
    tree = treelib.Tree()
    g = p.find('goals')

    if len(g.getchildren()) == 0:
        return tree

    id = last_id
    last_id += 1
    gr = g.getchildren()[0] #root
    tn = tree.create_node(gr.attrib['name'],id)
    tn.fraction = float(gr.attrib['importance'])
    tn.value = float(gr.attrib['progress'])
    if gr.attrib.has_key('deadline'):
        tn.deadline = gr.attrib['deadline']     # not used in this app
    else:
        tn.deadline = None

    add_subtree(tree, tn, gr, id)

    return tree

def add_subtree(tree, tn, gn, id):
    global last_id
    for i, gc in enumerate(gn.getchildren()):
        if gc.tag == 'goal':
            #cid = id + '.' + str(i)
            cid = last_id
            last_id += 1
            tc = tree.create_node(gc.attrib['name'], cid, tn.identifier)
            tc.fraction = float(gc.attrib['importance'])
            tc.value = float(gc.attrib['progress'])
            if gc.attrib.has_key('deadline'):
                tc.deadline = gc.attrib['deadline']     # not used in this app
            else:
                tc.deadline = None
            
            add_subtree(tree, tc, gc, cid)


def write_subtree(tree,tr,gr):
    for i in tr.fpointer:
        tn = tree.get_node(i)
        attrs = {'name':tn.tag, 'importance':str(tn.fraction), 'progress':str(tn.value)}
        if tn.deadline is not None:
            attrs['deadline'] = tn.deadline
        gn = ET.SubElement(gr, 'goal', attrs)
        write_subtree(tree,tn,gn)


def writeGSP(tree, path):
    tr = tree.get_node(tree.root)
    dr = ET.Element('project', {'type':'Mokuteki', 'version':__version__})
    gsp_tree = ET.ElementTree(dr)
    #TODO header maybe
    gsr = ET.SubElement(dr,'goals')
    attrs = {'name':tr.tag, 'importance':str(tr.fraction), 'progress':str(tr.value)}
    if tr.deadline is not None:
        attrs['deadline'] = tr.deadline
    gr = ET.SubElement(gsr, 'goal', attrs)

    write_subtree(tree,tr,gr)
    gsp_tree.write(path,pretty_print = True)
    


def draw_tree(tree, ax, center=(0.5,0.5), radius=0.5):
    width = radius/tree_depth(tree, tree.root)
    draw_node(tree.get_node(tree.root), tree, center, width, width, 0, 0, 360, ax)
    ax.set_aspect('equal')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

def calc_progress(tree, node):
    ns = tree.get_node(node)
    if len(ns.fpointer) == 0:
        return ns.value*(ns.fraction/100.0)
    else:
        prog = np.sum(map(lambda x: calc_progress(tree, x), ns.fpointer)) 
        ns.value = prog
        return prog*(ns.fraction/100.0)

class AppForm(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.setWindowTitle('Interactive sunburst')
        if len(sys.argv) != 2:
            print "specify .gsp file"
            sys.exit(1)
            #treefile = 'projekty.gsp'
        else:
            treefile = sys.argv[1]

        self.fulltree = readGSP(treefile)
        self.subtree = self.fulltree.subtree(self.fulltree.root)
        self._selected = None

        self.create_menu() 
        self.create_main_frame()

        self.on_draw()

    @property
    def selected(self):
        return self._selected

    
    @selected.setter
    def selected(self, val):
        self._selected = val
        if val is None:
            self.textbox.setText('')
            self.slider_label.setText('Importance (%)')
            self.prog_slider_label.setText('Progress (%)')



    def on_pick(self, event):
        id = event.artist.get_label()
        print "%s - %s" % (id, event.artist)        
        if self.selected is None or self.selected != id:
            self.selected = id
            ns = self.fulltree.get_node(id)
            self.textbox.setText(ns.tag)
            self.slider_label.setText('Importance %f %%' % ns.fraction)
            self.slider.setValue(ns.fraction)
            self.prog_slider_label.setText('Progress %f %%' % ns.value)
            self.prog_slider.setValue(ns.value)
        else:
            self.selected = None
        self.on_draw()
    
    def switch_root(self):
        if self.selected is not None:
            self.subtree = self.fulltree.subtree(self.selected)
        self.selected = None
        self.on_draw()

    def go_up(self):
        parent_id = self.fulltree.get_node(self.subtree.root).bpointer
        if parent_id is not None:
            self.subtree = self.fulltree.subtree(parent_id )
        self.selected = None
        self.on_draw()

    def change_portion(self):
        if self.selected is None or self.selected == self.subtree.root:
            return
        ns = self.fulltree.get_node(self.selected)
        delta = float(self.slider.value()) - ns.fraction
        if np.abs(delta) < 1:
            return
        sibs = self.fulltree.get_node(ns.bpointer).fpointer
        delta_sib = delta/len(sibs)

        for s in sibs:
            self.fulltree.get_node(s).fraction -= delta_sib

        ns.fraction += delta
        self.on_draw()

    def change_progress(self):
        if self.selected is None: 
            return
        ns = self.fulltree.get_node(self.selected)
        if len(ns.fpointer) > 0:
            return
        ns.value = self.prog_slider.value()
        calc_progress(self.fulltree, self.fulltree.root)
        self.subtree = self.fulltree.subtree(self.subtree.root) #regenerate subtree
        self.on_draw()



    
    def add_child(self):
        global last_id
        if self.selected is None:
            return
        ns = self.fulltree.get_node(self.selected)
        if len(ns.fpointer) != 0:
            print "add children only to leaves"
            return
        t = self.fulltree.create_node('new node', last_id, self.selected)
        last_id += 1
        t.fraction = 100.0
        self.subtree = self.fulltree.subtree(self.subtree.root) #regenerate subtree

        self.on_draw()



    def add_sibling(self):
        global last_id
        if self.selected == self.subtree.root:
            print "do not add siblings to subtree root"
            return
        ns = self.fulltree.get_node(self.selected)
        sibs = list(self.fulltree.get_node(ns.bpointer).fpointer)
        t = self.fulltree.create_node('new node', last_id, ns.bpointer)
        last_id += 1
        t.fraction = 100.0/(len(sibs)+1)

        ds = t.fraction/(len(sibs))
        for s in sibs:
            ts = self.fulltree.get_node(s)
            ts.fraction -= ds

        self.subtree = self.fulltree.subtree(self.subtree.root) #regenerate subtree
        self.slider.setValue(t.fraction)
        self.on_draw()
    
    def delete_node(self):
        if self.selected is None or self.selected == self.subtree.root:
            return

        self.fulltree.remove_node(self.selected)
        self.selected = None
        self.subtree = self.fulltree.subtree(self.subtree.root) #regenerate subtree
        self.on_draw()

        


        
    def change_tag(self):
        if self.selected is None:
            return
        ns = self.fulltree.get_node(self.selected)
        ns.tag = unicode(self.textbox.text())
        self.on_draw()

    def save_tree(self):
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '',"GSP (*.gsp)|*.gsp"
                        ))
        if path:
            writeGSP(self.fulltree, path)
            print 'Saved to %s' % path

    def load_tree(self):
        pass


    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        save_file_action = self.create_action("&Save",
            shortcut="Ctrl+S", slot=self.save_tree, 
            tip="Save to XML file")
        load_file_action = self.create_action("&Load",
            shortcut="Ctrl+O", slot=self.load_tree, 
            tip="Load from XML file")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (save_file_action,load_file_action, None, quit_action))
    
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
        
    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.gsp" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
        


    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        #self.fig = Figure((10.0, 10.0), dpi=self.dpi)
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        
        # Bind the 'pick' event for clicking on one of the bars
        self.canvas.mpl_connect('pick_event', self.on_pick)

        
        #self.fig.tight_layout()
        self.fig.subplots_adjust(top=0.99, right=0.99,left=0.01,bottom=0.01)
        # Other GUI controls
        # 
        self.textbox = QLineEdit()
        self.textbox.setMinimumWidth(200)
        self.connect(self.textbox, SIGNAL('editingFinished ()'), self.change_tag)
        
        self.focus_button = QPushButton("&Focus")
        self.connect(self.focus_button, SIGNAL('clicked()'), self.switch_root)

        self.up_button = QPushButton("&Up")
        self.connect(self.up_button, SIGNAL('clicked()'), self.go_up)

        self.add_sibling_button = QPushButton("&Add sibling")
        self.connect(self.add_sibling_button, SIGNAL('clicked()'), self.add_sibling)
        
        self.add_child_button = QPushButton("&Add child")
        self.connect(self.add_child_button, SIGNAL('clicked()'), self.add_child)
        
        self.delete_node_button = QPushButton("&Delete node")
        self.connect(self.delete_node_button, SIGNAL('clicked()'), self.delete_node)

        self.selected_label = QLabel('Selected:')

        self.slider_label = QLabel('Importance (%):')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0.01, 100)
        self.slider.setValue(20)
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.slider, SIGNAL('valueChanged(int)'), self.change_portion)
        
        self.prog_slider_label = QLabel('Progress (%):')
        self.prog_slider = QSlider(Qt.Horizontal)
        self.prog_slider.setRange(0.0, 100)
        self.prog_slider.setValue(0.0)
        self.prog_slider.setTracking(True)
        self.prog_slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.prog_slider, SIGNAL('valueChanged(int)'), self.change_progress)
        #
        # Layout with box sizers
        # 
        vbox = QVBoxLayout()
        
        vbox.addStretch(1)
        vbox.setSpacing(3)
        for w in [  self.selected_label, 
                    self.textbox, 
                    self.focus_button,
                    self.up_button,                     
                    self.slider_label, 
                    self.slider,
                    self.prog_slider_label, 
                    self.prog_slider,
                    self.add_sibling_button,
                    self.add_child_button,
                    self.delete_node_button 
                    ]:
            vbox.addWidget(w)
            vbox.setAlignment(w, Qt.AlignVCenter)
        vbox.addStretch(1)
        
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        self.canvas.setSizePolicy(sizePolicy)
        hbox.addWidget(self.canvas)

        hbox.addLayout(vbox)
        
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)

    def on_draw(self):
        """ Redraws the figure
        """
        self.axes.clear()  # clear the axes and redraw the plot anew      
        draw_tree(self.subtree, self.axes)
        
        self.canvas.draw()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()

