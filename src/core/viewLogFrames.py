import re
import sys,os
import curses, curses.textpad
import fileinput
import traceback
import logging

logging.basicConfig(filename="_viewLogFrames.log",level=logging.DEBUG)

global_separatorString = "--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"

def setupGlobalColors():
    global global_InBlockAttr, global_CursorAttr, global_NormalAttr, global_InvertAttr, global_SilentCursorAttr
    bkgd = curses.COLOR_WHITE
    colors = {}
    curses.init_pair(1,curses.COLOR_BLUE,bkgd)
    global_InBlockAttr = curses.color_pair(1)
    curses.init_pair(2,curses.COLOR_RED,curses.COLOR_YELLOW)
    global_CursorAttr  = curses.color_pair(2)
    curses.init_pair(3,curses.COLOR_BLACK,bkgd)
    global_NormalAttr = curses.color_pair(3)
    curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)
    global_InvertAttr = curses.color_pair(4)
    curses.init_pair(5,curses.COLOR_RED,curses.COLOR_WHITE)
    global_SilentCursorAttr = curses.color_pair(5)
    return colors


class Node:
    def __init__(self,headLine,headLineNumber):
        self._Children = []
        self._Parent = None
        self._PreviousSibling = None
        self._NextSibling = None
        self._Closed = True
        self._HeadLine = headLine
        self._HeadLineNumber = headLineNumber
        self._TailLine = None
        self._TailLineNumber = headLineNumber

    def openAllParents(self):
        parent = self.parent()
        if ( parent != None ):
            parent.setClosed(False)
            parent.openAllParents()

    def closeAllChildren(self):
        self._Closed = True
        for c in self._Children:
            c.closeAllChildren()

    def children(self):
        return self._Children

    def hasNoChildren(self):
        return len(self._Children)==0

    def hasChildren(self):
        return len(self._Children)!=0

    def hasHeadOnly(self):
#        return ( ( self._TailLine == None ) or ( self._TailLine == "}" ) )
        return self._TailLine == None

    def getHeadLine(self):
        return self._HeadLine

    def getHeadLineNumber(self):
        return self._HeadLineNumber

    def getTailLineNumber(self):
        return self._TailLineNumber

    def getLineCount(self):
        return self._TailLineNumber - self._HeadLineNumber+1

    def getTailLine(self):
        assert self._TailLine!=None
        return self._TailLine

    def setHeadLine(self, line):
        self._HeadLine = line

    def setTailLine(self,line,lineNumber):
        self._TailLine = line
        self._TailLineNumber = lineNumber

    def addChild(self,c):
        if ( len(self._Children) > 0 ):
            c.setPreviousSibling(self._Children[-1])
        else:
            c.setPreviousSibling(None)
        self._Children.append(c)
        c.setParent(self)

    def parent(self):
        return self._Parent

    def setParent(self,p):
        self._Parent = p

    def previousSibling(self):
        return self._PreviousSibling

    def nextSibling(self):
        return self._NextSibling

    def setPreviousSibling(self,p):
        self._PreviousSibling = p
        if ( p != None ):
            p._NextSibling = self

    def setClosed(self,op):
        self._Closed = op

    def isClosed(self):
              # if there are no children then it is automatically open
        if ( self._Children == [] ):
            return False
        return self._Closed






def NodeCrawler_copy(nodeCrawler):
    return NodeCrawler(nodeCrawler.node(),nodeCrawler.atHead())

class NodeCrawler:
    def __init__(self,node,atHead):
        self._Node = node
        self._AtHead = atHead

    def atHead(self):
        return self._AtHead

    def isValid(self):
        return ( self._Node != None )

    def getCurrentLineNumber(self):
        if ( self._AtHead ):
            return self._Node.getHeadLineNumber()
        return self._Node.getTailLineNumber()

    def getCurrentLine(self):
        if ( self._AtHead ):
            return self._Node.getHeadLine()
        return self._Node.getTailLine()

    def node(self):
        return self._Node

    def text(self):
        if ( not self.isValid() ):
            return ""
        if ( self._AtHead ):
            content = self._Node.getHeadLine()
        else:
            content = self._Node.getTailLine()
        if ( self._Node.hasChildren() ):
            if ( self._Node.isClosed() ):
                header = "+.."
            else:
                header = "-  "
        else:
            header = "   "
        lines = "%6d"%self._Node.getLineCount()
        return header+lines+" "+content

    def isOnEmptyTail(self):
        if ( self._AtHead ):
            return False
        if ( self._Node.getTailLine() == "}" ):
            return True
        return False



        # Return a NodeCrawler 
    def crawlToPreviousOnce(self,doNotEnterClosed):
        if ( self._Node == None ):
            return self
        if ( self._AtHead ):
            previous = self._Node.previousSibling()
            if ( previous == None ):
                return NodeCrawler(self._Node.parent(),True)
            return NodeCrawler(previous,previous.hasHeadOnly())
        # we are at the tail of a node
        if ( self._Node.isClosed() and doNotEnterClosed ):
            return NodeCrawler(self._Node,True)  # move to the head of this node
        if ( self._Node.hasNoChildren() ):
            return NodeCrawler(self._Node,True)  # No children - move to the head of this node
        # at tail, open and have children -> move to the last child
        previous = self._Node.children()[-1]
        return NodeCrawler(previous,previous.hasHeadOnly())

    def crawlToPrevious(self,doNotEnterClosed):
        if ( self._Node == None ):
            return self
        done = False
        maxSteps = 100
        cur = self
        while (not done):
            cur = cur.crawlToPreviousOnce(doNotEnterClosed)
            if ( not cur.isValid() ):
                return cur
            if ( not cur.isOnEmptyTail() ):
                return cur
            maxSteps = maxSteps - 1
            if ( maxSteps < 0 ):
                raise "crawlToPreviousOnce too many times"

    def crawlToPreviousDoNotEnterClosed(self):
        return self.crawlToPrevious(True)

    def crawlToPreviousEnterClosed(self):
        return self.crawlToPrevious(False)


    def crawlToNextOnce(self,doNotEnterClosed):
        if ( self._Node == None ):
            return self
        if ( not self._AtHead ):
            # we are on the tail of a node
            next = self._Node.nextSibling()
            if ( next == None ):
                # no next sibling so crawl up to the parent
                parent = self._Node.parent()
                return NodeCrawler(parent,False)
            return NodeCrawler(next,True)
        # we are at the head of a node
        if ( self._Node.hasHeadOnly() ):
            # and the node only has a head
            next = self._Node.nextSibling()
            if ( next == None ):
                # crawl up to the parent and move to its tail
                parent = self._Node.parent()
                return NodeCrawler(parent,False)
            return NodeCrawler(next,True)
        # we are at the head of a node and it has a tail
        if ( self._Node.isClosed() and doNotEnterClosed ):
            # since the node is closed move to its tail
            return NodeCrawler(self._Node,False)
        if ( self._Node.hasNoChildren() ):
            # the node is open but has no children, move to its tail
            return NodeCrawler(self._Node,False)
        # we are at the head, the node is open and it has children
        next = self._Node.children()[0]
        return NodeCrawler(next,True)


    def crawlToNext(self,doNotEnterClosed):
        if ( self._Node == None ):
            return self
        done = False
        cur = self
        maxSteps = 100
        while (not done):
            cur = cur.crawlToNextOnce(doNotEnterClosed)
            if ( not cur.isValid() ):
                return cur
            if ( not cur.isOnEmptyTail() ):
                return cur
            maxSteps = maxSteps - 1
            if ( maxSteps < 0 ):
                raise "crawlToPreviousOnce too many times"


    def crawlToNextDoNotEnterClosed(self):
        return self.crawlToNext(True)

    def crawlToNextEnterClosed(self):
        return self.crawlToNext(False)

    def crawlToParentNode(self):
        cur = NodeCrawler(self._Node.parent(),True)
        return cur




class TreeBuilder:
    def __init__(self):
        self._RootNode = Node("{Entire tree",0)
        self._RootNode.setTailLine("}",0)
        self._RootNode.setClosed(False)
        self._Depth = 0
        self._Stack = [self._RootNode]
        self._LineNumber = 0

    def rootNode(self):
        return self._RootNode

    def addLine(self,line,lineNumber):
        firstChar = line[0]
        if ( firstChar == "{" ):
            self._Depth = self._Depth + 1
            node = Node(line,lineNumber)
            node.setHeadLine(line)
            self._Stack[-1].addChild(node)
            self._Stack.append(node)
        elif ( firstChar == "}" ):
            self._Depth = self._Depth - 1
            node = self._Stack.pop()
            node.setTailLine(line,lineNumber)
        else:
            node = Node(line,lineNumber)
            self._Stack[-1].addChild(node)
        self._LineNumber = self._LineNumber + 1

    def depth(self):
        return self._Depth

    def fillInMissingLines(self,lastLineNumber):
        for d in range(0,self._Depth):
            self.addLine("}",lastLineNumber)
            lastLineNumber = lastLineNumber + 1
        return lastLineNumber

    def buildFromFileInput(self):
        lineNumber = 0
        for rawline in fileinput.input():
            line = rawline[:-1]
            if ( line != "" ):
                builder.addLine(line,lineNumber)
            lineNumber = lineNumber + 1
        lineNumber = builder.fillInMissingLines(lineNumber)
        self._RootNode.setTailLine("}",lineNumber)







class FoldFrame:
    def __init__(self,foldManager,nodeCrawler):
        self._Manager = foldManager
        self._NodeCrawlerCursor = NodeCrawler_copy(nodeCrawler)

    def setDimensions(self,top,height,width,hasSeparator):
        self._Top = top
        self._Window = self._Manager.window().subwin(height,width,top,0)
        self._HasSeparator = hasSeparator
        if ( hasSeparator ):
            self._Height = height-1
        else:
            self._Height = height
        self._Width = width
        self._Lines = [None]*self._Height
        self._Cursor = 0

    def nodeCrawlerCursor(self):
        return self._NodeCrawlerCursor

    def updateLines(self):
        previousNode = self._NodeCrawlerCursor.crawlToPreviousDoNotEnterClosed()
        for c in range(self._Cursor-1,-1,-1):
            self._Lines[c] = previousNode
            previousNode = previousNode.crawlToPreviousDoNotEnterClosed()
        curNode = self._NodeCrawlerCursor
        for c in range(self._Cursor,self._Height):
            self._Lines[c] = curNode
            curNode = curNode.crawlToNextDoNotEnterClosed()
            
    def redrawLines(self):
        global global_CursorAttr, global_NormalAttr, global_InBlockAttr, global_SilentCursorAttr, global_InvertAttr
        onHeadLineNumber = self._NodeCrawlerCursor.node().getHeadLineNumber()
        onTailLineNumber = self._NodeCrawlerCursor.node().getTailLineNumber()
        for c in range(0,self._Height):
            lineNode = self._Lines[c]
            if ( not lineNode.isValid() ):
                continue
            if ( self._Cursor == c ):
                if ( self == self._Manager.currentFrame() ):
                    attr = global_CursorAttr
                else:
                    attr = global_SilentCursorAttr
            else:
                curLineNumber = lineNode.getCurrentLineNumber()
                if ( (onHeadLineNumber <= curLineNumber ) and ( curLineNumber < onTailLineNumber ) ):
                    attr = global_InBlockAttr
                else:
                    attr = global_NormalAttr
            logging.debug("addnstr: window dim(%s) c(%d) text(%s) self._Width(%d) attr(%s)"%(self._Window.getmaxyx(),c,lineNode.text(),self._Width,attr))
            self._Window.addnstr(c,0,lineNode.text(),self._Width,attr)
            self._Window.clrtoeol()
        if ( self._HasSeparator ):
            global global_separatorString
            logging.debug("separator: window dim(%s) ypos(%d) attr(%s)"%(self._Window.getmaxyx(),self._Height,global_InvertAttr)) 
            self._Window.addnstr(self._Height,0,global_separatorString,self._Width,global_NormalAttr)
        self._Window.clrtobot()
        self._Window.refresh()

    def cursorUp(self):
        if ( self._Cursor > 0 ):
            self._Cursor = self._Cursor-1
        previous = self._NodeCrawlerCursor.crawlToPreviousDoNotEnterClosed()
        if ( previous.isValid() ):
            self._NodeCrawlerCursor = previous

    def pageUp(self):
        for x in range(0,self._Height-1):
            previous = self._NodeCrawlerCursor.crawlToPreviousDoNotEnterClosed()
            if ( previous.isValid() ):
                self._NodeCrawlerCursor = previous

    def cursorDown(self):
        if ( self._Cursor < (self._Height-1) ):
            self._Cursor = self._Cursor + 1
        next = self._NodeCrawlerCursor.crawlToNextDoNotEnterClosed()
        if ( next.isValid() ):
            self._NodeCrawlerCursor = next

    def pageDown(self):
        for x in range(0,self._Height-1):
            next = self._NodeCrawlerCursor.crawlToNextDoNotEnterClosed()
            if ( next.isValid() ):
                self._NodeCrawlerCursor = next


    def openCurrentNode(self):
        self._NodeCrawlerCursor.node().setClosed(False)

    def closeCurrentNode(self):
        self._NodeCrawlerCursor.node().setClosed(True)

    def toggleCurrentNode(self):
        if ( self._NodeCrawlerCursor.node().isClosed() ):
            self._NodeCrawlerCursor.node().setClosed(False)
        else:
            self._NodeCrawlerCursor.node().setClosed(True)




    def closeAllChildren(self):
        node = self._NodeCrawlerCursor.node()
        node.closeAllChildren()

    def forwardSearch(self,searchString):
        search = re.compile(searchString)
        cur = self._NodeCrawlerCursor.crawlToNextEnterClosed()
        while ( cur.isValid() ):
            if ( search.search(cur.getCurrentLine()) != None ):
                self._NodeCrawlerCursor = cur
                break
            cur = cur.crawlToNextEnterClosed()
        if ( not cur.isValid() ):
            return "FAILED Forward search <%s>"%searchString
        self._NodeCrawlerCursor.node().openAllParents()
        return "Successful forward search <%s>" % searchString

    def reverseSearch(self,searchString):
        search = re.compile(searchString)
        cur = self._NodeCrawlerCursor.crawlToPreviousEnterClosed()
        while ( cur.isValid() ):
            if ( search.search(cur.getCurrentLine()) != None ):
                self._NodeCrawlerCursor = cur
                break
            cur = cur.crawlToPreviousEnterClosed()
        if ( not cur.isValid() ):
            return "FAILED Reverse search <%s>" % searchString
        self._NodeCrawlerCursor.node().openAllParents()
        return "Successful reverse search <%s>" % searchString

    def parentNode(self):
        cur = self._NodeCrawlerCursor.crawlToParentNode()
        if ( cur.isValid() ):
            self._NodeCrawlerCursor = cur

    def setNodeCrawlerCursor(self,c):
        self._NodeCrawlerCursor = c


class FoldManager:
    def __init__(self,window,rootNode):
        global global_NormalAttr
        curses.start_color()
        setupGlobalColors()
        self._Window = window
        self._RootNode = rootNode
        self._Locations = {}
        self._Window.bkgd(" ",global_NormalAttr)
        (h,w) = window.getmaxyx()
        self._Height = h-2
        self._InfoLine = h-2
        self._InputLine = h-1
        self._Width = w
        self._LastSearch = "EXCEPTION"
        self._Frames = []
        firstFrame = FoldFrame(self,NodeCrawler(rootNode,True))
        self._Frames.append(firstFrame)
        self._CurrentFrameIndex = 0
        self.balanceFrames()

    def window(self):
        return self._Window

    def currentFrame(self):
        return self._Frames[self._CurrentFrameIndex]

    def redrawInfoLine(self,msg):
        global global_InvertAttr
        self._Window.addnstr(self._InfoLine,0,msg+(" "*200),self._Width,global_InvertAttr)
        self._Window.clrtoeol()

    def redrawInputLine(self,msg):
        self._Window.addstr(self._InputLine,0,msg)
        self._Window.clrtoeol()

    def redrawAll(self,statusMessage,inputMessage):
        for f in self._Frames:
            f.redrawLines()
        self.redrawInfoLine(statusMessage)
        self.redrawInputLine(inputMessage)
        self._Window.refresh()

    def updateFrames(self):
        for f in self._Frames:
            f.updateLines()

    def enterSearchString(self,searchType):
        msg = "%s <%s>: " % (searchType, self._LastSearch )
        self._Window.addstr(self._InputLine,0,msg)
        self._Window.clrtoeol()
        subwin = self._Window.subwin(1,self._Width-len(msg)-2,self._InputLine,len(msg)+1)
        self._Window.refresh()
        textbox = curses.textpad.Textbox(subwin)
        textbox.stripspaces = True
        rawSearch = textbox.edit()
        search = rawSearch.strip()
        if ( search != "" ):
            self._LastSearch = search
        extraMessage = "Forward search <%s>" % self._LastSearch
        return extraMessage

    def nextFrame(self):
        self._CurrentFrameIndex = self._CurrentFrameIndex+1
        if ( self._CurrentFrameIndex >= len(self._Frames) ):
            self._CurrentFrameIndex = 0

    def balanceFrames(self):
        numberOfFrames = len(self._Frames)
        heightOfEach = int(self._Height/numberOfFrames)
        idx = 0
        top = 0
        for f in self._Frames[:-1]:
            # reset the positions/heights and whether the frame has a separator
            f.setDimensions(top,heightOfEach,self._Width,True)
            top = top + heightOfEach
            idx = idx + 1
        self._Frames[idx].setDimensions(top,self._Height-top,self._Width,False)

    def insertFrameBeforeCurrent(self):
        newFrame = FoldFrame(self,self.currentFrame().nodeCrawlerCursor())
        self._Frames.insert(self._CurrentFrameIndex,newFrame)
        self._CurrentFrameIndex = self._CurrentFrameIndex + 1
        self.balanceFrames()

    def deleteCurrentFrame(self):
        if ( len(self._Frames) == 1 ):
            return
        self._Frames.remove(self._Frames[self._CurrentFrameIndex])
        if ( self._CurrentFrameIndex >= len(self._Frames) ):
            self._CurrentFrameIndex = self._CurrentFrameIndex-1
        self.balanceFrames()

    def cursorStatus(self,extraMessage):
        return "viewLog line(%s) %s" % (self.currentFrame().nodeCrawlerCursor().node().getHeadLineNumber(), extraMessage )





    def mainloop(self):
        curses.raw()
        self.updateFrames()
        self.redrawAll("viewLog","startup")
        while (1):
            c = self._Window.getch()
            extraMessage = ""
            if ( c == curses.KEY_UP ):
                self.currentFrame().cursorUp()
            elif (c == curses.KEY_DOWN ):
                self.currentFrame().cursorDown()
            elif (c == ord("t") or c == ord(" ") ):
                self.currentFrame().toggleCurrentNode()
            elif (c == ord("o") ):
                self.currentFrame().openCurrentNode()
            elif (c == ord("c") ):
                self.currentFrame().closeCurrentNode()
            elif (c == 22 ): # C-v
                self.currentFrame().pageDown()
            elif (c == 118 ): # M-v
                self.currentFrame().pageUp()
            elif ( c == ord("C") ):
                self.currentFrame().nodeCrawlerCursor().node().closeAllChildren()
            elif ( c == ord("u") ):
                self.currentFrame().parentNode()
            elif (c == 19 ): # C-s
                self.enterSearchString("Forward search")
                extraMessage = self.currentFrame().forwardSearch(self._LastSearch)
            elif (c == 18 ): # C-r
                self.enterSearchString("Reverse search")
                extraMessage = self.currentFrame().reverseSearch(self._LastSearch)
            elif ( c == ord("m") ):
                m = self._Window.getch()
                self._Locations[m] = self.currentFrame().nodeCrawlerCursor()
                extraMessage = "Saved location in register <%c>" % m
            elif ( c == ord("'") ):
                m = self._Window.getch()
                if ( m in self._Locations ):
                    self.currentFrame().setNodeCrawlerCursor(self._Locations[m])
                    self.currentFrame().nodeCrawlerCursor().node().openAllParents()
                    extraMessage = "Restored location in register <%c>" % m
                else:
                    extraMessage = "Unknown register <%c>" % m
            elif ( c == 24 ):
                m = self._Window.getch()
                if ( m == ord("2") ):
                    self.insertFrameBeforeCurrent()
                elif ( m == ord("o") ):
                    self.nextFrame()
                elif ( m == ord("0") ):
                    self.deleteCurrentFrame()
            elif (c == ord("Q") or ( c == 3 ) ):
                return
            elif (curses.keyname(c) == "^v" ):
                self.pageDown()
            statusLine = self.cursorStatus(extraMessage)
            self._Window.erase()
            self.updateFrames()
            self.redrawAll(statusLine,"last key: %d" % c)

#
#
#
# I'm not sure I need the classes below
#
#
#

class FoldLine:
    def __init__(self,toggleable,closed,text,startLine,node):
        self._Toggleable = toggleable
        self._Closed = closed
        self._Text = text
        self._StartLine = startLine
        self._Node = node


class FoldTree:
    def __init__(self,text,topNode):
        self._Text = text
        self._TopNode = topNode

class FoldTreeViewer:
    def __init__(self,folds):
        self._FoldTree = folds
        self._Lines = []
        self._Height = 24

    def rebuildAllWithSubnode(self,topNode,lines,lineCounter):
        for n in topNode.children():
            if ( not c.isOpen() ):
                lines.append(c.head())
                lines.append("+.."+c.head())
                lines.append("..."+c.tail())
            






def main(win,rootNode):
    (height,width) = win.getmaxyx()
    viewer = FoldManager(win,rootNode)
    viewer.mainloop()






if __name__=='__main__':
  builder = TreeBuilder()
  builder.buildFromFileInput()
  rootNode = builder.rootNode()
  try:
      # Initialize curses
      stdscr=curses.initscr()
      # Turn off echoing of keys, and enter cbreak mode,
      # where no buffering is performed on keyboard input
      curses.noecho()
      curses.cbreak()

      # In keypad mode, escape sequences for special keys
      # (like the cursor keys) will be interpreted and
      # a special value like curses.KEY_LEFT will be returned
      stdscr.keypad(1)
      main(stdscr,rootNode)                    # Enter the main loop
      # Set everything back to normal
      stdscr.keypad(0)
      curses.echo()
      curses.nocbreak()
      curses.endwin()                 # Terminate curses
  except:
      # In event of error, restore terminal to sane state.
      stdscr.keypad(0)
      curses.echo()
      curses.nocbreak()
      curses.endwin()
      traceback.print_exc()           # Print the exception


