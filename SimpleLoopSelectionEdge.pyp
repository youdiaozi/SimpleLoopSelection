import c4d
import os

from c4d import gui, plugins, bitmaps

#be sure to use a unique ID obtained from https://plugincafe.maxon.net/c4dpluginid_cp
PLUGIN_ID = 1053305

#for GeLoadString（IDS IDM 无法以c4d.的形式调用?）
# Control IDs (1001+)
ID_SIMPLELOOPSELECTIONEDGE_TIPS1                    = 1001
ID_SIMPLELOOPSELECTIONEDGE_TIPS2                    = 1002
ID_SIMPLELOOPSELECTIONEDGE_TIPS3                    = 1003
ID_SIMPLELOOPSELECTIONEDGE_TIPS4                    = 1004
                                                
ID_SIMPLELOOPSELECTIONEDGE_OP                       = 1010
ID_SIMPLELOOPSELECTIONEDGE_ORIGINEDGEINDICES        = 1011
ID_SIMPLELOOPSELECTIONEDGE_SELECTEDEDGEINDICES      = 1012
                                                
# Control String IDs (50000+)                      
IDS_SIMPLELOOPSELECTIONEDGE_TOOLTIP                 = 50000
IDS_SIMPLELOOPSELECTIONEDGE_TIPS1                   = 50001
IDS_SIMPLELOOPSELECTIONEDGE_TIPS2                   = 50002
IDS_SIMPLELOOPSELECTIONEDGE_TIPS3                   = 50003
IDS_SIMPLELOOPSELECTIONEDGE_TIPS4                   = 50004
                                                
IDS_SIMPLELOOPSELECTIONEDGE_OP                      = 50010
IDS_SIMPLELOOPSELECTIONEDGE_ORIGINEDGEINDICES       = 50011
IDS_SIMPLELOOPSELECTIONEDGE_SELECTEDEDGEINDICES     = 50012
                                                
# Menu String IDs (50000+)                         
IDS_SIMPLELOOPSELECTIONEDGE_MENU1                   = 50100
IDS_SIMPLELOOPSELECTIONEDGE_MENU2                   = 50110    
IDS_SIMPLELOOPSELECTIONEDGE_MENU3                   = 50120
IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU1            = 50121
IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU2            = 50122
IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU3            = 50123
IDS_SIMPLELOOPSELECTIONEDGE_MENU4                   = 50124
                                                
# Menu IDs (900000+，c4d.FIRST_POPUP_ID)           
IDM_SIMPLELOOPSELECTIONEDGE_MENU1                   = 900000 # c4d.FIRST_POPUP_ID = 900000
IDM_SIMPLELOOPSELECTIONEDGE_MENU2                   = 900010    
IDM_SIMPLELOOPSELECTIONEDGE_MENU3                   = 900020
IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU1            = 900021
IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU2            = 900022
IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU3            = 900023
IDM_SIMPLELOOPSELECTIONEDGE_MENU4                   = 900030

DIRECTION_NONE = 0
DIRECTION_UP = 1
DIRECTION_DOWN = 2
DIRECTION_LEFT = 3
DIRECTION_RIGHT = 4
DIRECTION_LOOP = 5

"""
怎么变换鼠标图标?
怎么加粗DrawLine2D
"""

class StringHelper():
    @staticmethod
    def DirectionToString(direction):
        strings = { DIRECTION_NONE: "DIRECTION_NONE", DIRECTION_UP: "DIRECTION_UP", DIRECTION_DOWN: "DIRECTION_DOWN", DIRECTION_LEFT: "DIRECTION_LEFT", DIRECTION_RIGHT: "DIRECTION_RIGHT", DIRECTION_LOOP: "DIRECTION_LOOP" }
        return strings[direction]

class ArrayHelper():
    @staticmethod
    def GetIndex(arr, value):
        if arr:
            for i in xrange(len(arr)):
                if arr[i] == value:
                    return i
            
        return -1
        
    
    """
    返回：arr1中除去在arr2中有的元素
    ----------------------------------
    @important: 数组[]作为参数传入时，视为 None?
    """
    @staticmethod
    def RemoveSame(arr1, arr2):
        if arr1 and arr2:
            return [value for value in arr1 if value not in arr2]
        elif arr1:
            return arr1
        
        return []
                
# =========== BaseDraw helper =============== 
class BaseDrawHelper():   
    """
    ViewportSelect.Init 时，不能使用 bd.GetFrameScreen，只能使用 bd.GetFrame，
    否则引发 ViewportSelect 的 Object not initiallized exception
    """
    @staticmethod
    def GetFrameWidthHeight(bd):
        frame = bd.GetFrame()
        left = frame["cl"]
        right = frame["cr"]
        top = frame["ct"]
        bottom = frame["cb"]

        width = right - left + 1
        height = bottom - top +1
        
        return width, height
    
    @staticmethod
    def WindowToFrameScreen(bd, mx, my):
        frame = bd.GetFrameScreen()
        left = frame["cl"]
        top = frame["ct"]
        sx = mx - left
        sy = my - top + 22
        
        return sx, sy
        
    """
    WindowToFrameScreen 时，需要+22，而 FrameScreenToWindow 时，不能-22 ?    
    # ---------------------------------------------------------------------
    # GetCursorInfo 得到的是 FrameScreen Coor. x y
    # MouseInput 得到的是 FrameScreen Coor. sx sy
    # bd.DrawCircle2D 使用的是 FrameScreen Coor. sx sy
    # ----------------------------
    # GetInputState 得到的是 Window Coor. mx my
    # ----------------------------
    # ViewportSelect.Init 使用的是 Frame Coor.
    """      
    @staticmethod
    def FrameScreenToWindow(bd, sx, sy):
        frame = bd.GetFrameScreen()
        left = frame["cl"]
        top = frame["ct"]
        mx = sx + left
        my = sy + top # 不能-22
        
        return mx, my
# =========== end: BaseDraw helper ===============


class EdgeHelper():
    nbr = None
    op = None
    
    _edgeIndex = -1
    _p1 = -1 # point1Index
    _p2 = -1 # point2Index
    _originEdgeIndex1 = -1 # origin selected edge index(greater)
    _originEdgeIndex2 = -1 # origin selected edge index(smaller)
        
    def __init__(self, op, nbr):
        self.op = op
        self.nbr = nbr
        
    def __eq__(self, other):
        # and self.op == other.op and self.nbr == other.nbr
        return (self.p1 == other.p1 and self.p2 == other.p2) or (self.p1 == other.p2 and self.p2 == other.p1)
        
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __str__(self):
        p1pos, p2pos = self.GetPointsPosition()
        msg = "{0} --- p1:{1}, p2:{2} --- [{3}, {4}]".format(self.edgeIndex, self.p1, self.p2, p1pos, p2pos)
        return msg
    
    @property
    def p1(self):
        return self._p1
        
    @property
    def p2(self):
        return self._p2
    
    @property
    def edgeIndex(self):
        return self._edgeIndex
    
    """
    计算鼠标位置下的edgeIndex（已转换成op/nbr的格式）
    ------------------------------------
    viewportSelect.GetPixelInfoEdge得到的值是info["i"] = 4*polyIndex+side，即0-1-2-3，4-5-6-7，8-9-10-11
    而op、nbr的所有计算，如GetSelectedEdges、GetEdgeCount、GetEdgePolys、GetPolyInfo等，都是按0-1-2-3，(2)-4-5-6，(5)-7-8-9的形式计算
    """
    def GetEdgeIndexUnderMouse(self, doc, bd, sx, sy):
        if not self.op.IsInstanceOf(c4d.Opolygon): return -1 # 未C的对象会引发 ViewportSelect.Init 的 Exception

        try:
            width, height = BaseDrawHelper.GetFrameWidthHeight(bd)
            
            viewportSelect = c4d.utils.ViewportSelect()
            viewportSelect.Init(width, height, bd, [self.op], c4d.Mpolyedgepoint, True, c4d.VIEWPORTSELECTFLAGS_IGNORE_HIDDEN_SEL)
            
            #info = viewportSelect.GetPixelInfoEdge(sx, sy) # 难以选择上
            info = viewportSelect.GetNearestEdge(self.op, sx, sy) # GetNearestEdge 更容易选择
            viewportSelect.ClearPixelInfo(sx, sy, c4d.VIEWPORT_CLEAR_EDGE)
            
            if info: 
                nonuniqueIndex = info["i"]
                
                polyIndex, side = divmod(nonuniqueIndex, 4) # info["i"] = 4*polyIndex+side，见注释
                pli = self.nbr.GetPolyInfo(polyIndex)                
                if pli:
                    edgeIndex = pli["edge"][side]
                    return edgeIndex
        except Exception, e:
            print "err:", e
            return -1
            
        return -1

    """
    由edgeIndex计算p1 p2
    edgeIndex无法用@edgeIndex.setter的形式实现?
    """
    def SetEdgeIndex(self, value):
        allpolys = self.op.GetAllPolygons()
        
        for i in xrange(self.op.GetPolygonCount()):
            if allpolys[i].c == allpolys[i].d: # 去掉三角面等
                continue
                
            pli = self.nbr.GetPolyInfo(i)            
            for side in xrange(4):
                # 去掉三角面等
                # if pli["mark"][side] or (side == 2 and allpolys[i].c == allpolys[i].d):
                    # continue
                #print "pedge:", pli["edge"][side], " value:",value
                
                if side == 0 and pli["edge"][side] == value:
                    self._edgeIndex = value
                    self._p1, self._p2 = allpolys[i].a, allpolys[i].b
                    return
                elif side == 1 and pli["edge"][side] == value:
                    self._edgeIndex = value
                    self._p1, self._p2 = allpolys[i].b, allpolys[i].c
                    return
                elif side == 2 and pli["edge"][side] == value:
                    self._edgeIndex = value
                    self._p1, self._p2 = allpolys[i].c, allpolys[i].d
                    return
                elif side == 3 and pli["edge"][side] == value:
                    self._edgeIndex = value
                    self._p1, self._p2 = allpolys[i].d, allpolys[i].a
                    return
                
        self._edgeIndex = -1

    def SwapEqual(self, a, b, p1, p2):
        return (a == p1 and b == p2) or (b == p1 and a == p2)            
    
    # 由p1 p2计算edgeIndex，避免单独赋值p1 p2，造成重复计算
    def SetPoints(self, p1, p2):
        self._p1, self._p2 = p1, p2
        
        allpolys = self.op.GetAllPolygons()
        
        for i in xrange(self.op.GetPolygonCount()):
            pli = self.nbr.GetPolyInfo(i)
            for side in xrange(4):
                # 去掉三角面等
                if pli["mark"][side] or (side == 2 and allpolys[i].c == allpolys[i].d):
                    continue

                if side == 0 and self.SwapEqual(allpolys[i].a, allpolys[i].b, p1, p2):
                    self._edgeIndex = pli["edge"][side]
                    return
                elif side == 1 and self.SwapEqual(allpolys[i].b, allpolys[i].c, p1, p2):
                    self._edgeIndex = pli["edge"][side]
                    return
                elif side == 2 and self.SwapEqual(allpolys[i].c, allpolys[i].d, p1, p2):
                    self._edgeIndex = pli["edge"][side]
                    return
                elif side == 3 and self.SwapEqual(allpolys[i].d, allpolys[i].a, p1, p2):
                    self._edgeIndex = pli["edge"][side]
                    return
                
        self._edgeIndex = -1
        
    def GetPointPosition(self, pointIndex):
        count = self.op.GetPointCount()
        if pointIndex >= 0 and pointIndex < count:
            return self.op.GetPoint(pointIndex)
        
        return None
    
    """
    计算p1 p2的position(local)——因为op.GetPoint()返回的是local，所以GetPointsPosition()返回的也是local
    """
    def GetPointsPosition(self):
        return self.GetPointPosition(self.p1), self.GetPointPosition(self.p2)
        
    """
    @for 已选择的edge索引数组（重叠的不算）
    @remark 总edge数：nbr.GetEdgeCount() # 重叠的不算
            已选择的edge数：edges.GetCount()
    """
    def GetSelectedEdgeIndices(self):
        edges = c4d.BaseSelect()
        edges = self.op.GetSelectedEdges(self.nbr, c4d.EDGESELECTIONTYPE_SELECTION)
        #edges = self.op.GetEdgeS() # GetEdgeS会把重叠的也算进去
                   
        edgeIndices = []
        for index in xrange(self.nbr.GetEdgeCount()): #  GetEdgeCount 重叠的不算
            if edges.IsSelected(index):
                edgeIndices.append(index)
                
        return edgeIndices
    
    """
    默认：False替换
    isAdd = True，则添加；False，则替换
    """
    def SetSelectedEdgeIndices(self, edgeIndices, isAdd=False):
        edges = c4d.BaseSelect()
        if isAdd:
            edges = self.op.GetSelectedEdges(self.nbr, c4d.EDGESELECTIONTYPE_SELECTION)
            #edges = self.op.GetEdgeS()
        else:
            edges = self.op.GetSelectedEdges(self.nbr, c4d.EDGESELECTIONTYPE_SELECTION)
            edges.DeselectAll()
            
        for edgeIndex in edgeIndices:
            edges.Select(edgeIndex)
        
        return self.op.SetSelectedEdges(self.nbr, edges, c4d.EDGESELECTIONTYPE_SELECTION)
                
    # ---------------- Up / Down -------------------
    # 大在前
    def GetOriginEdgeIndices(self):
        if self._originEdgeIndex2 == -1:
            if self._originEdgeIndex1 == -1:
                return []
            else:
                return [self._originEdgeIndex1]
        else:
            return [self._originEdgeIndex1, self._originEdgeIndex2]
    
    # 大在前
    def SetOriginEdgeIndices(self, originEdgeIndices):
        if not originEdgeIndices or len(originEdgeIndices) == 0:
            self._originEdgeIndex1, self._originEdgeIndex2 = -1, -1
        elif len(originEdgeIndices) == 1:
            self._originEdgeIndex1, self._originEdgeIndex2 = originEdgeIndices[0], -1
        elif len(originEdgeIndices) == 2:
            #self._originEdgeIndex1, self._originEdgeIndex2 = max(originEdgeIndices), min(originEdgeIndices)        
            originEdgeIndices.sort(reverse = True)
            self._originEdgeIndex1, self._originEdgeIndex2 = originEdgeIndices[0], originEdgeIndices[1]
        else:
            originEdgeIndices = originEdgeIndices[-2:]
            #self._originEdgeIndex1, self._originEdgeIndex2 = max(originEdgeIndices), min(originEdgeIndices)
            originEdgeIndices.sort(reverse = True)
            self._originEdgeIndex1, self._originEdgeIndex2 = originEdgeIndices[0], originEdgeIndices[1]
    
    def GetOppositeEdge(self, polyIndex):
        if polyIndex == -1:
            return None
        
        oppositeEdgeIndex = -1
        
        allpolys = self.op.GetAllPolygons()
        poly = allpolys[polyIndex]
        if poly.c == poly.d: return None # 三角面等
        
        pli = self.nbr.GetPolyInfo(polyIndex)
        
        for side in xrange(4):      
            if side == 0 and self.SwapEqual(poly.a, poly.b, self.p1, self.p2):
                oppositeEdgeIndex = pli["edge"][(side+2)%4]
                break
            elif side == 1 and self.SwapEqual(poly.b, poly.c, self.p1, self.p2):
                oppositeEdgeIndex = pli["edge"][(side+2)%4]
                break
            elif side == 2 and self.SwapEqual(poly.c, poly.d, self.p1, self.p2):
                oppositeEdgeIndex = pli["edge"][(side+2)%4]
                break
            elif side == 3 and self.SwapEqual(poly.d, poly.a, self.p1, self.p2):
                oppositeEdgeIndex = pli["edge"][(side+2)%4]
                break
                
        if oppositeEdgeIndex != -1:
            oppositeEdge = EdgeHelper(self.op, self.nbr)
            oppositeEdge.SetEdgeIndex(oppositeEdgeIndex)
            return oppositeEdge
            
        return None
    
    def GetUpDownStepDistance(self):
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        
        startEdge = EdgeHelper(self.op, self.nbr)
        startEdge.SetEdgeIndex(originEdgeIndex2)  # 起点2，edgeIndex小的边
        endEdge = EdgeHelper(self.op, self.nbr)
        endEdge.SetEdgeIndex(originEdgeIndex1) # 起点1，edgeIndex大的边为up(start -> end)
        
        first, second = self.nbr.GetEdgePolys(startEdge.p1, startEdge.p2)
        
        # stepDistance 指起点2到起点1的间隔edge数（+1）
        stepDistance = 0
        meetflag = False
        breakflag = False
        # 以下计算主要是获取 meetflag 和 stepDistance 的值
        #print "|---start,end:", startEdge, endEdge
        while first != -1:
            oppositeEdge = startEdge.GetOppositeEdge(first)
            #print "|---oppp:", oppositeEdge, " temp:", tempcount
            if oppositeEdge and oppositeEdge.edgeIndex != -1:
                stepDistance += 1
                
                # 遇到起点1，结束stepDistance计算
                if oppositeEdge.edgeIndex == endEdge.edgeIndex:
                    meetflag = True
                    break
                    
                # 遇到起点2（原自己），跳出无限循环，直接返回
                if oppositeEdge.edgeIndex == originEdgeIndex2:
                    breakflag = True
                    break
                
                startEdge = oppositeEdge
                first = self.nbr.GetNeighbor(oppositeEdge.p1, oppositeEdge.p2, first)                
            else:
                break
                
        # 反向查找
        stepDistance2 = 0
        meetflag2 = False
        breakflag2 = False
        #startEdge = EdgeHelper(self.op, self.nbr)
        startEdge.SetEdgeIndex(originEdgeIndex2)  # 起点2，edgeIndex小的边
        #print "|===start,end:", startEdge, endEdge
        first, second = self.nbr.GetEdgePolys(startEdge.p1, startEdge.p2)
        # 以下计算主要是获取 meetflag2 和 stepDistance2 的值
        while second != -1:
            oppositeEdge = startEdge.GetOppositeEdge(second)
            #print "|===oppp:", oppositeEdge, " temp:", tempcount
            if oppositeEdge and oppositeEdge.edgeIndex != -1:
                stepDistance2 += 1
                
                # 遇到起点1，结束stepDistance2计算
                if oppositeEdge.edgeIndex == endEdge.edgeIndex:
                    meetflag2 = True
                    break
                    
                # 遇到起点2（原自己），跳出无限循环，直接返回
                if oppositeEdge.edgeIndex == originEdgeIndex2:
                    breakflag2 = True
                    break
                
                startEdge = oppositeEdge
                second = self.nbr.GetNeighbor(oppositeEdge.p1, oppositeEdge.p2, second)        
            else:
                break     
        
        if meetflag and meetflag2:
            if stepDistance < stepDistance2:
                return DIRECTION_UP, stepDistance
            else:
                return DIRECTION_DOWN, stepDistance2            
        elif meetflag:
            return DIRECTION_UP, stepDistance
        elif meetflag2:
            return DIRECTION_DOWN, stepDistance2
        else:        
            return DIRECTION_NONE, 0
    
    """
    获取downEdges（按edgeIndex小的边向不是大的边的方向）
    """
    def GetDownEdgeIndices(self, direction, stepDistance):
        if self._originEdgeIndex1 == -1 or self._originEdgeIndex2 == -1 or not (direction in [DIRECTION_UP, DIRECTION_DOWN]):
            return None

        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2        
        
        if stepDistance >= 1:
            #print "|---downEdgeIndices:", downEdgeIndices
            # 按步分析，按down方向由原来的endEdge前进
            downEdgeIndices = []
            
            startEdge = EdgeHelper(self.op, self.nbr)
            if direction == DIRECTION_UP:
                startEdge.SetEdgeIndex(originEdgeIndex2) # 由起点2开始
            else: # DIRECTION_DOWN
                startEdge.SetEdgeIndex(originEdgeIndex1) # 由起点1开始            
            
            first, second = self.nbr.GetEdgePolys(startEdge.p1, startEdge.p2)
            breakflag = False
            meetflag2 = False
            while second != -1:           
                for st in xrange(stepDistance):                
                    oppositeEdge = startEdge.GetOppositeEdge(second)
                    if oppositeEdge and oppositeEdge.edgeIndex != -1:
                        startEdge = oppositeEdge
                        second = self.nbr.GetNeighbor(oppositeEdge.p1, oppositeEdge.p2, second)
                    else:
                        breakflag = True
                        break # break for
                
                if breakflag:
                    break # break while（需要2个break才能跳出2层循环）
                
                # 一圈后的起点1
                if (direction == DIRECTION_UP) and (startEdge.edgeIndex == originEdgeIndex1):
                    meetflag2 = True
                    break
                    
                # 一圈后的起点2
                if (direction == DIRECTION_DOWN) and (startEdge.edgeIndex == originEdgeIndex2):
                    meetflag2 = True
                    break

                # 添加得到的downEdge
                downEdgeIndices.append(startEdge.edgeIndex)
                
            if meetflag2: pass # 暂时不需要处理 
            
            return downEdgeIndices
            
        # 没有找到
        return None
    
    """"
    获取upEdges（按edgeIndex小的边向大的边的方向）
    """
    def GetUpEdgeIndices(self, direction, stepDistance):
        if self._originEdgeIndex1 == -1 or self._originEdgeIndex2 == -1 or not (direction in [DIRECTION_UP, DIRECTION_DOWN]):
            return None

        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        
        if stepDistance >= 1:
            #print "|---upEdgeIndices:", upEdgeIndices
            # 按步分析，按up方向由原来的endEdge前进
            upEdgeIndices = []
            
            startEdge = EdgeHelper(self.op, self.nbr)
            if direction == DIRECTION_UP:
                startEdge.SetEdgeIndex(originEdgeIndex1) # 由起点1开始
            else: # DIRECTION_DOWN
                startEdge.SetEdgeIndex(originEdgeIndex2) # 由起点2开始            
            
            first, second = self.nbr.GetEdgePolys(startEdge.p1, startEdge.p2)
            breakflag = False
            meetflag2 = False
            while first != -1:           
                for st in xrange(stepDistance):                
                    oppositeEdge = startEdge.GetOppositeEdge(first)
                    if oppositeEdge and oppositeEdge.edgeIndex != -1:
                        startEdge = oppositeEdge
                        first = self.nbr.GetNeighbor(oppositeEdge.p1, oppositeEdge.p2, first)
                    else:
                        breakflag = True
                        break # break for
                
                if breakflag:
                    break # break while（需要2个break才能跳出2层循环）
                
                # 一圈后的起点2
                if (direction == DIRECTION_UP) and (startEdge.edgeIndex == originEdgeIndex2):
                    meetflag2 = True
                    break
                    
                # 一圈后的起点1
                if (direction == DIRECTION_DOWN) and (startEdge.edgeIndex == originEdgeIndex1):
                    meetflag2 = True
                    break

                # 添加得到的upEdge
                upEdgeIndices.append(startEdge.edgeIndex)
                
            if meetflag2: pass # 暂时不需要处理                
            
            return upEdgeIndices
            
        # 没有找到
        return None

    """    
    返回：tuple(stepAmount, edgeIndices)，方便stepAmount达到应该的最大值时-1操作
    ----------------------------
    stepAmount可以任意整数，正数表示UpEdges，0表示origin，-1表示起点2（edgeIndex小的边），负数表示DownEdges
    当正数超过UpEdges数时，加上DownEdges；当负数超过DownEdges数时，加上UpEdges。
    """
    def GetUpDownEdgeIndicesByStepAmount(self, stepAmount):
        edgeIndices = []
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2        
        
        
        direction, stepDistance = self.GetUpDownStepDistance()
        #print "ADirection:", direction
        if stepDistance == 0: # 不在一个方向上
            return 0, None
        
        #print "StepAmount:", stepAmount # 这个值up最大时可能会+1，down最小时可能会-1
        
        if stepAmount == -1: # 返回起点2
            if direction == DIRECTION_UP:
                edgeIndices.append(originEdgeIndex2)
            else:
                edgeIndices.append(originEdgeIndex1)
        elif stepAmount == 0: # 没有+/-时，返回origin
            edgeIndices.extend([originEdgeIndex2, originEdgeIndex1])
        else:
            upEdgeIndices = self.GetUpEdgeIndices(direction, stepDistance)
            if not upEdgeIndices:
                upEdgeIndices = []
            downEdgeIndices = self.GetDownEdgeIndices(direction, stepDistance)
            if not downEdgeIndices:
                downEdgeIndices = []
            #print "up:", upEdgeIndices, " down:", downEdgeIndices
            
            if stepAmount > 0: # origin2/1 + 部分/全部upEdgeIndices + 部分downEdgeIndices
                # 去除down中up有的元素，防止同一个edgeIndex重复添加
                downEdgeIndices = ArrayHelper.RemoveSame(downEdgeIndices, upEdgeIndices)
                
                # 超过可达到的最大 stepAmount，则保留参数
                stepAmount = min(stepAmount, len(upEdgeIndices) + len(downEdgeIndices))
                
                allIndices = [originEdgeIndex2, originEdgeIndex1] # 加上origin
                allIndices.extend(upEdgeIndices)
                allIndices.extend(downEdgeIndices)
                
                edgeIndices = allIndices[:stepAmount+2]
                    
            else: # stepAmount < -1 --> origin2 + 部分/全部downEdgeIndices + origin1 + 部分upEdgeIndices 
                # 去除up中down有的元素，防止同一个edgeIndex重复添加
                upEdgeIndices = ArrayHelper.RemoveSame(upEdgeIndices, downEdgeIndices)
                
                # 超过可达到的最小 stepAmount，则保留参数
                stepAmount = max(stepAmount, -(len(upEdgeIndices) + len(downEdgeIndices) + 2))
                
                if direction == DIRECTION_UP:
                    allIndices = [originEdgeIndex2] # 加上origin2
                else:
                    allIndices = [originEdgeIndex1] # 加上origin1
                
                allIndices.extend(downEdgeIndices)
                
                if direction == DIRECTION_UP:
                    allIndices.append(originEdgeIndex1) # 加上origin1
                else:
                    allIndices.append(originEdgeIndex2) # 加上origin2
                
                allIndices.extend(upEdgeIndices)
                
                edgeIndices = allIndices[:-stepAmount]
                    
        return stepAmount, edgeIndices
            
    # ---------------- end: Up / Down -------------------
    
    # ---------------- Left / Right -------------------    
    def GetRightCornerEdge(self, currentEdge, polyIndex):        
        if not currentEdge or polyIndex == -1:
            return None
        
        allpolys = self.op.GetAllPolygons()        
        
        poly = allpolys[polyIndex]
        if poly.c == poly.d: return None # 三角面等
        
        pli = self.nbr.GetPolyInfo(polyIndex)
        
        for side in xrange(4):
            if side == 0 and self.SwapEqual(poly.a, poly.b, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+3)%4] # cornerEdge指跟右边点垂直的edge
                break
            elif side == 1 and self.SwapEqual(poly.b, poly.c, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+3)%4]
                break
            elif side == 2 and self.SwapEqual(poly.c, poly.d, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+3)%4]
                break
            elif side == 3 and self.SwapEqual(poly.d, poly.a, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+3)%4]
                break
            
        if cornerEdgeIndex != -1:
            cornerEdge = EdgeHelper(self.op, self.nbr)
            cornerEdge.SetEdgeIndex(cornerEdgeIndex)
            return cornerEdge
        
        return None
        
    def GetLeftCornerEdge(self, currentEdge, polyIndex):        
        if not currentEdge or polyIndex == -1:
            return None
        
        allpolys = self.op.GetAllPolygons()        
        
        poly = allpolys[polyIndex]
        if poly.c == poly.d: return None # 三角面等
        
        pli = self.nbr.GetPolyInfo(polyIndex)
        cornerEdgeIndex = -1
        for side in xrange(4):
        
            if side == 0 and self.SwapEqual(poly.a, poly.b, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+1)%4] # cornerEdge指跟左边点垂直的edge
                break
            elif side == 1 and self.SwapEqual(poly.b, poly.c, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+1)%4]
                break
            elif side == 2 and self.SwapEqual(poly.c, poly.d, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+1)%4]
                break
            elif side == 3 and self.SwapEqual(poly.d, poly.a, currentEdge.p1, currentEdge.p2):
                cornerEdgeIndex = pli["edge"][(side+1)%4]
                break            
            
            #print "   |===side:", side, " cornerEdge:", cornerEdgeIndex, " cur:", currentEdge
        
        
        if cornerEdgeIndex != -1:
            cornerEdge = EdgeHelper(self.op, self.nbr)
            cornerEdge.SetEdgeIndex(cornerEdgeIndex)
            #print "cornerEdge:", cornerEdge
            return cornerEdge
        
        return None
    
    def GetRightNearbyEdge(self):
        nearbyEdgeIndex = -1
        
        allpolys = self.op.GetAllPolygons()
        cornerEdge = self
        # 按 first 方向 Right 找
        first, second = self.nbr.GetEdgePolys(cornerEdge.p1, cornerEdge.p2)
        if first != -1:
            cornerEdge = self.GetRightCornerEdge(cornerEdge, first)       
            if cornerEdge:
                first = self.nbr.GetNeighbor(cornerEdge.p1, cornerEdge.p2, first)
                if first != -1:
                    cornerEdge = self.GetRightCornerEdge(cornerEdge, first)
                else:
                    cornerEdge = None
        else:        
            cornerEdge = None
        
        if not cornerEdge:
            # 按 second 方向 Left 找            
            cornerEdge = self # 重置 cornerEdge 为 self，即回到起点换方向重新搜索
            first, second = self.nbr.GetEdgePolys(cornerEdge.p1, cornerEdge.p2)
            
            if second != -1:
                cornerEdge = self.GetLeftCornerEdge(cornerEdge, second)                
                if cornerEdge:
                    second = self.nbr.GetNeighbor(cornerEdge.p1, cornerEdge.p2, second)
                    if second != -1:
                        cornerEdge = self.GetLeftCornerEdge(cornerEdge, second)
                    else:
                        cornerEdge = None
            else:        
                cornerEdge = None
        
        if cornerEdge:
            return cornerEdge
            
        return None
    
    def GetLeftNearbyEdge(self):
        nearbyEdgeIndex = -1
        
        allpolys = self.op.GetAllPolygons()
        cornerEdge = self
        # 按 first 方向 Left 找
        first, second = self.nbr.GetEdgePolys(cornerEdge.p1, cornerEdge.p2)
        if first != -1:
            cornerEdge = self.GetLeftCornerEdge(cornerEdge, first)
            if cornerEdge:
                first = self.nbr.GetNeighbor(cornerEdge.p1, cornerEdge.p2, first)
                if first != -1:
                    cornerEdge = self.GetLeftCornerEdge(cornerEdge, first)
                else:
                    cornerEdge = None
            else:
                cornerEdge = None
        else:        
            cornerEdge = None
                
        if not cornerEdge:
            # 按 second 方向 Right 找            
            cornerEdge = self # 重置 cornerEdge 为 self，即回到起点换方向重新搜索
            first, second = self.nbr.GetEdgePolys(cornerEdge.p1, cornerEdge.p2)
            if second != -1:
                cornerEdge = self.GetRightCornerEdge(cornerEdge, second)
                if cornerEdge:
                    second = self.nbr.GetNeighbor(cornerEdge.p1, cornerEdge.p2, second)
                    if second != -1:
                        cornerEdge = self.GetRightCornerEdge(cornerEdge, second)
                    else:
                        cornerEdge = None
                else:
                    cornerEdge = None
            else:        
                cornerEdge = None
        
        if cornerEdge:
            return cornerEdge
            
        return None
   
    def GetLeftRightStepDistance(self):
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        #print "|---o1o2:", originEdgeIndex1, originEdgeIndex2
        
        startEdge = EdgeHelper(self.op, self.nbr)
        startEdge.SetEdgeIndex(originEdgeIndex2)  # 起点2，edgeIndex小的边
        endEdge = EdgeHelper(self.op, self.nbr)
        endEdge.SetEdgeIndex(originEdgeIndex1) # 起点1，edgeIndex大的边为right(start -> end)
        
        # stepDistance 指起点2到起点1的间隔edge数（+1）
        stepDistance = 0
        meetflag = False
        breakflag = False
        #print "sign1"
        # 以下计算主要是获取 meetflag 和 stepDistance 的值
        while startEdge:
            nearbyEdge = startEdge.GetLeftNearbyEdge()
            #print "|---nearbyEdge:", nearbyEdge
            if nearbyEdge and nearbyEdge.edgeIndex != -1:
                stepDistance += 1
                
                # 遇到起点1，结束stepDistance计算
                if nearbyEdge.edgeIndex == endEdge.edgeIndex:
                    meetflag = True
                    break
                    
                # 遇到起点2（原自己），跳出无限循环，直接返回
                if nearbyEdge.edgeIndex == originEdgeIndex2:
                    breakflag = True
                    break
                
            startEdge = nearbyEdge
        
        # 反向查找
        startEdge = EdgeHelper(self.op, self.nbr)
        startEdge.SetEdgeIndex(originEdgeIndex2)  # 起点2，edgeIndex小的边
        stepDistance2 = 0
        meetflag2 = False
        breakflag2 = False
        #print "sign3:", nearbyEdge
        tempcount = 0
        while startEdge:
            nearbyEdge = startEdge.GetRightNearbyEdge()
            #print "|===nearbyEdge:", nearbyEdge
            if nearbyEdge and nearbyEdge.edgeIndex != -1:
                stepDistance2 += 1
                
                # 遇到起点1，结束stepDistance计算
                if nearbyEdge.edgeIndex == endEdge.edgeIndex:
                    meetflag2 = True
                    break
                    
                # 遇到起点2（原自己），跳出无限循环，直接返回
                if nearbyEdge.edgeIndex == originEdgeIndex2:
                    breakflag2 = True
                    break
                
            startEdge = nearbyEdge
        
        #print "m,mm:", meetflag, meetflag2
        if meetflag and meetflag2:
            if stepDistance < stepDistance2:
                return DIRECTION_LEFT, stepDistance
            else:
                return DIRECTION_RIGHT, stepDistance2            
        elif meetflag:
            return DIRECTION_LEFT, stepDistance
        elif meetflag2:
            return DIRECTION_RIGHT, stepDistance2
        else:        
            return DIRECTION_NONE, 0

    """
    获取leftEdges（按edgeIndex小的边向不是大的边的方向）
    """
    def GetLeftEdgeIndices(self, direction, stepDistance):
        if self._originEdgeIndex1 == -1 or self._originEdgeIndex2 == -1 or not (direction in [DIRECTION_LEFT, DIRECTION_RIGHT]):
            return None

        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
                
        if stepDistance >= 1:
            # 按步分析，按left方向向不是原来的endEdge前进
            leftEdgeIndices = []
            
            startEdge = EdgeHelper(self.op, self.nbr)
            if direction == DIRECTION_LEFT:
                startEdge.SetEdgeIndex(originEdgeIndex1) # 由起点1开始
            else: # DIRECTION_RIGHT
                startEdge.SetEdgeIndex(originEdgeIndex2) # 由起点2开始

            breakflag = False
            meetflag2 = False
            while startEdge:
                for st in xrange(stepDistance):
                    nearbyEdge = startEdge.GetLeftNearbyEdge()
                    
                    if nearbyEdge and nearbyEdge.edgeIndex != -1:
                        startEdge = nearbyEdge
                    else:
                        breakflag = True
                        break # break for
                
                if breakflag:
                    break # break while（需要2个break才能跳出2层循环）
                
                # 一圈后的起点2
                if direction == DIRECTION_LEFT and (startEdge.edgeIndex == originEdgeIndex2):
                    meetflag2 = True
                    break
                    
                # 一圈后的起点1
                if direction == DIRECTION_RIGHT and (startEdge.edgeIndex == originEdgeIndex1):
                    meetflag2 = True
                    break

                # 添加得到的leftEdge
                leftEdgeIndices.append(startEdge.edgeIndex)
                
            if meetflag2: pass # 暂时不需要处理
            
            return leftEdgeIndices
            
        # 没有找到
        return []

    """
    获取rightEdges（按edgeIndex小的边向大的边的方向）
    """
    def GetRightEdgeIndices(self, direction, stepDistance):
        if self._originEdgeIndex1 == -1 or self._originEdgeIndex2 == -1 or not (direction in [DIRECTION_LEFT, DIRECTION_RIGHT]):
            return None

        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        
        if stepDistance >= 1:            
            # 按步分析，按right方向向原来的endEdge前进
            rightEdgeIndices = []
            
            startEdge = EdgeHelper(self.op, self.nbr)
            if direction == DIRECTION_LEFT:
                startEdge.SetEdgeIndex(originEdgeIndex2) # 由起点2开始
            else: # DIRECTION_RIGHT
                startEdge.SetEdgeIndex(originEdgeIndex1) # 由起点1开始

            breakflag = False
            meetflag2 = False
            while startEdge:
                for st in xrange(stepDistance):
                    nearbyEdge = startEdge.GetRightNearbyEdge()
                    
                    if nearbyEdge and nearbyEdge.edgeIndex != -1:
                        startEdge = nearbyEdge
                    else:
                        breakflag = True
                        break # break for
                
                if breakflag:
                    break # break while（需要2个break才能跳出2层循环）
                
                # 一圈后的起点1
                if direction == DIRECTION_LEFT and (startEdge.edgeIndex == originEdgeIndex1):
                    meetflag2 = True
                    break
                    
                # 一圈后的起点2
                if direction == DIRECTION_RIGHT and (startEdge.edgeIndex == originEdgeIndex2):
                    meetflag2 = True
                    break

                # 添加得到的rightEdge
                rightEdgeIndices.append(startEdge.edgeIndex)
                
            if meetflag2: pass # 暂时不需要处理
            
            return rightEdgeIndices
            
        # 没有找到
        return []
    
    """    
    返回：trightle(stepAmount, edgeIndices)，方便stepAmount达到应该的最大值时-1操作
    ----------------------------
    stepAmount可以任意整数，正数表示RightEdges，0表示origin，-1表示起点2（edgeIndex小的边），负数表示LeftEdges
    当正数超过RightEdges数时，加上LeftEdges；当负数超过LeftEdges数时，加上RightEdges。
    """
    def GetLeftRightEdgeIndicesByStepAmount(self, stepAmount):
        edgeIndices = []
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2        
        
        direction, stepDistance = self.GetLeftRightStepDistance()
        #print "|---stepDistance:", stepDistance
        if stepDistance == 0: # 不在一个方向上
            return 0, None
        
        #print "|---Want StepAmount:", stepAmount # 这个值right最大时可能会+1，left最小时可能会-1
        
        if stepAmount == -1: # 返回起点2
            if direction == DIRECTION_RIGHT:
                edgeIndices.append(originEdgeIndex2)
            else:
                edgeIndices.append(originEdgeIndex1)
        elif stepAmount == 0: # 没有+/-时，返回origin
            edgeIndices.extend([originEdgeIndex2, originEdgeIndex1])
        else:
            rightEdgeIndices = self.GetRightEdgeIndices(direction, stepDistance)
            if not rightEdgeIndices:
                rightEdgeIndices = []
            leftEdgeIndices = self.GetLeftEdgeIndices(direction, stepDistance)
            if not leftEdgeIndices:
                leftEdgeIndices = []            
            #print "|---right:", rightEdgeIndices, " left:", leftEdgeIndices
            
            if stepAmount > 0: # origin2/1 + 部分/全部rightEdgeIndices + 部分leftEdgeIndices
                # 去除left中right有的元素，防止同一个edgeIndex重复添加
                leftEdgeIndices = ArrayHelper.RemoveSame(leftEdgeIndices, rightEdgeIndices)
                
                # 超过可达到的最大 stepAmount，则保留参数
                stepAmount = min(stepAmount, len(rightEdgeIndices) + len(leftEdgeIndices))
                
                allIndices = [originEdgeIndex2, originEdgeIndex1] # 加上origin
                allIndices.extend(rightEdgeIndices)
                allIndices.extend(leftEdgeIndices)
                
                edgeIndices = allIndices[:stepAmount+2]
                    
            else: # stepAmount < -1 --> origin2 + 部分/全部leftEdgeIndices + origin1 + 部分rightEdgeIndices 
                # 去除right中left有的元素，防止同一个edgeIndex重复添加
                rightEdgeIndices = ArrayHelper.RemoveSame(rightEdgeIndices, leftEdgeIndices)
                
                # 超过可达到的最小 stepAmount，则保留参数
                stepAmount = max(stepAmount, -(len(rightEdgeIndices) + len(leftEdgeIndices) + 2))
                
                if direction == DIRECTION_RIGHT:
                    allIndices = [originEdgeIndex2] # 加上origin2
                else:
                    allIndices = [originEdgeIndex1] # 加上origin1
                    
                allIndices.extend(leftEdgeIndices)
                
                if direction == DIRECTION_RIGHT:
                    allIndices.append(originEdgeIndex1) # 加上origin1
                else:
                    allIndices.append(originEdgeIndex2) # 加上origin2
                
                allIndices.extend(rightEdgeIndices)
                
                edgeIndices = allIndices[:-stepAmount]
                    
        return stepAmount, edgeIndices
    
    # ---------------- end: Left / Right -------------------    
        
    # ---------------- loop in other direction -------------------    
    """
    UpDownLoop 即 LeftRightEdges
    """
    def GetUpDownLoopEdgeIndices(self):
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        
        allIndices = []
        stepAmount = 100
        
        # origin1
        edge = EdgeHelper(self.op, self.nbr)
        edge.SetEdgeIndex(originEdgeIndex1)
        tempOrigin2 = edge.GetRightNearbyEdge()
        if not tempOrigin2 or tempOrigin2.edgeIndex == -1:
            tempOrigin2 = edge.GetLeftNearbyEdge()
        
        if tempOrigin2 and tempOrigin2.edgeIndex != -1:
            edge.SetOriginEdgeIndices([originEdgeIndex1, tempOrigin2.edgeIndex])
            direction, stepDistance = edge.GetLeftRightStepDistance()
            if stepDistance != 0:
                stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(stepAmount)
                if edgeIndices:
                    allIndices.extend(edgeIndices)
            
        # origin2
        edge = EdgeHelper(self.op, self.nbr)
        edge.SetEdgeIndex(originEdgeIndex2)
        tempOrigin2 = edge.GetRightNearbyEdge()
        if not tempOrigin2 or tempOrigin2.edgeIndex == -1:
            tempOrigin2 = edge.GetLeftNearbyEdge()
        
        if tempOrigin2 and tempOrigin2.edgeIndex != -1:
            edge.SetOriginEdgeIndices([originEdgeIndex2, tempOrigin2.edgeIndex])
            direction, stepDistance = edge.GetLeftRightStepDistance()
            if stepDistance != 0:
                stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(stepAmount)
                if edgeIndices:
                    allIndices.extend(edgeIndices)
        
        return allIndices
    
    """
    LeftRightLoop 即 UpDownEdges
    """
    def GetLeftRightLoopEdgeIndices(self):
        originEdgeIndex1, originEdgeIndex2 = self._originEdgeIndex1, self._originEdgeIndex2
        
        allIndices = []
        stepAmount = 100
        
        # origin1
        edge = EdgeHelper(self.op, self.nbr)
        edge.SetEdgeIndex(originEdgeIndex1)
        first, second = self.nbr.GetEdgePolys(edge.p1, edge.p2)
        tempOrigin2 = edge.GetOppositeEdge(first)
        if not tempOrigin2 or tempOrigin2.edgeIndex == -1:            
            tempOrigin2 = edge.GetOppositeEdge(second)
        
        if tempOrigin2 and tempOrigin2.edgeIndex != -1:
            edge.SetOriginEdgeIndices([originEdgeIndex1, tempOrigin2.edgeIndex])
            direction, stepDistance = edge.GetUpDownStepDistance()
            if stepDistance != 0:
                stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(stepAmount)
                if edgeIndices:
                    allIndices.extend(edgeIndices)
            
        # origin2
        edge = EdgeHelper(self.op, self.nbr)
        edge.SetEdgeIndex(originEdgeIndex2)
        first, second = self.nbr.GetEdgePolys(edge.p1, edge.p2)
        tempOrigin2 = edge.GetOppositeEdge(first)
        if not tempOrigin2 or tempOrigin2.edgeIndex == -1:            
            tempOrigin2 = edge.GetOppositeEdge(second)
        
        if tempOrigin2 and tempOrigin2.edgeIndex != -1:
            edge.SetOriginEdgeIndices([originEdgeIndex2, tempOrigin2.edgeIndex])
            direction, stepDistance = edge.GetUpDownStepDistance()
            if stepDistance != 0:
                stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(stepAmount)
                if edgeIndices:
                    allIndices.extend(edgeIndices)
        
        return allIndices
    
    # ---------------- end: loop in other direction -------------------    

class SimpleLoopSelectionEdgeDialog(gui.SubDialog):
    parameters = None

    """"
    接收 ToolData 参数，引用方式同步
    """
    def __init__(self, arg):
        self.parameters = arg

    def CreateLayout(self):
        # ========== 当前信息 ==========
        self.GroupBegin(id=1000, flags=c4d.BFH_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(10, 0, 10, 0)
        
        # OP
        opName = "None"
        if self.parameters["OP"]:
            opName = self.parameters["OP"][c4d.ID_BASELIST_NAME]
        infoOPText = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_OP, opName)
        self.infoOP = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_OP, flags=c4d.BFH_MASK, name=infoOPText, borderstyle=c4d.BORDER_NONE)
        
        # OriginEdgeIndices
        originEdgeIndices = "[]"
        if self.parameters["OriginEdgeIndices"]:
            originEdgeIndices = self.parameters["OriginEdgeIndices"]
        infoOriginEdgeIndicesText = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_ORIGINEDGEINDICES, originEdgeIndices)
        self.infoOriginEdgeIndices = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_ORIGINEDGEINDICES, flags=c4d.BFH_MASK, name=infoOriginEdgeIndicesText, borderstyle=c4d.BORDER_NONE)
        
        # SelectedEdgeIndices
        selectedEdgeIndices = "[]"
        if self.parameters["SelectedEdgeIndices"]:
            selectedEdgeIndices = self.parameters["SelectedEdgeIndices"]
        infoSelectedEdgeIndicesText = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_SELECTEDEDGEINDICES, selectedEdgeIndices)
        self.infoSelectedEdgeIndices = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_SELECTEDEDGEINDICES, flags=c4d.BFH_MASK, name=infoSelectedEdgeIndicesText, borderstyle=c4d.BORDER_NONE)        
        
        self.GroupEnd()
        # ========== end: 当前信息 ==========
        
        self.AddSeparatorH(500)
        
        # ========== 文字提示 ==========
        self.GroupBegin(id=1000, flags=c4d.BFH_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(10, 0, 10, 0)
        
        tipsText1 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_TIPS1)
        self.tips1 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_TIPS1, flags=c4d.BFH_MASK, name=tipsText1, borderstyle=c4d.BORDER_NONE)
        
        tipsText2 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_TIPS2)
        self.tips2 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_TIPS2, flags=c4d.BFH_MASK, name=tipsText2, borderstyle=c4d.BORDER_NONE)
        
        tipsText3 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_TIPS3)
        self.tips3 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_TIPS3, flags=c4d.BFH_MASK, name=tipsText3, borderstyle=c4d.BORDER_NONE)
        
        tipsText4 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_TIPS4)
        self.tips4 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONEDGE_TIPS4, flags=c4d.BFH_MASK, name=tipsText4, borderstyle=c4d.BORDER_NONE)
        
        self.GroupEnd()
        # ========== end: 文字提示 ==========
        
        #self.AddButton(id=SIMPLELOOPSELECTIONEDGE_BUTTON, flags=c4d.BFH_LEFT|c4d.BFH_SCALE, initw=120, name="Button")
        
        return True

    def Command(self, id, msg):
        # if id == SIMPLELOOPSELECTIONEDGE_BUTTON:
            # pass
            
        return True
        
class SimpleLoopSelectionEdge(plugins.ToolData):
    parameters = None
    
    def __init__(self):
        self.parameters = {} # for SubDialog
        
        doc = c4d.documents.GetActiveDocument()
        op = doc.GetActiveObject()
        if op and op.IsInstanceOf(c4d.Opolygon):
            self.parameters["OP"] = op
        else:
            self.parameters["OP"] = None
            
        self.parameters["OriginEdgeIndices"] = -1
        self.parameters["SelectedEdgeIndices"] = -1
        self.parameters["LastOriginEdgeIndex"] = -1
        self.parameters["StepAmount"] = 0       
        
    def GetState(self, doc):
        if doc.GetMode()==c4d.Mpaint: return 0
        return c4d.CMD_ENABLED    
    
    def KeyboardInput(self, doc, data, bd, win, msg):
        key = msg.GetLong(c4d.BFM_INPUT_CHANNEL)
        cstr = msg.GetString(c4d.BFM_INPUT_ASC)
        #print "key {0} pressed.".format(cstr)
        
        if key == c4d.KEY_ESC: #do what you want
            
            return True #return True to signal that the key is processed
            
        op = doc.GetActiveObject()
        if op and op.IsInstanceOf(c4d.Opolygon):
            nbr = c4d.utils.Neighbor()
            nbr.Init(op)
            edge = EdgeHelper(op, nbr)            
            originEdgeIndices = []
            
            # 利用 self.parameters 初始化已有的参数
            if op == self.parameters["OP"]:
                originEdgeIndices = self.parameters["OriginEdgeIndices"]
                if not originEdgeIndices:
                    originEdgeIndices = []
            else:
                # ?未解决：切换op时，以当前选择的最后2个为origin（多个选择时，未/无需细分确认最后）
                selectedEdgeIndices = edge.GetSelectedEdgeIndices()
                if selectedEdgeIndices:
                    if len(selectedEdgeIndices) >= 2:
                        originEdgeIndices.extend(selectedEdgeIndices[-2:])
                    elif len(selectedEdgeIndices) == 1:
                        originEdgeIndices.append(selectedEdgeIndices[0])
            
            if len(originEdgeIndices) != 2:
                print "Please select 2 edges."
                return True

            # 以下2行很重要，先设置origin才可以计算
            edge.SetOriginEdgeIndices(originEdgeIndices)
            self.parameters["OriginEdgeIndices"] = edge.GetOriginEdgeIndices()
            self.parameters["OP"] = op
            
            flag = False
            if (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QCTRL):
                # [Ctrl+up/down] UpEdges/DownEdges
                if key == c4d.KEY_UP:
                    print "{0}".format("Ctrl+Up")
                    
                    self.parameters["StepAmount"] += 1
                    
                    stepAmount = 0
                    edgeIndices = None
                    direction, stepDistance = edge.GetUpDownStepDistance()
                    if stepDistance != 0:
                        stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(self.parameters["StepAmount"])
                    else:
                        direction, stepDistance = edge.GetLeftRightStepDistance()
                        if stepDistance != 0:
                            stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(self.parameters["StepAmount"])
                    
                    if edgeIndices:
                        print "ori:", originEdgeIndices, "direction:", StringHelper.DirectionToString(direction), " edges:", edgeIndices
                        edge.SetSelectedEdgeIndices(edgeIndices)
                        # 修改为 GetUpDownEdgeIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] -= 1
                        
                    flag = True
                    
                elif key == c4d.KEY_DOWN:
                    print "{0}".format("Ctrl+Down")
                    
                    self.parameters["StepAmount"] -= 1
                    
                    stepAmount = 0
                    edgeIndices = None
                    direction, stepDistance = edge.GetUpDownStepDistance()
                    if stepDistance != 0:
                        stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(self.parameters["StepAmount"])
                    else:
                        direction, stepDistance = edge.GetLeftRightStepDistance()
                        if stepDistance != 0:
                            stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(self.parameters["StepAmount"])
                    
                    if edgeIndices:
                        print "ori:", originEdgeIndices, "direction:", StringHelper.DirectionToString(direction), " edges:", edgeIndices
                        edge.SetSelectedEdgeIndices(edgeIndices)
                        # 修改为 GetUpDownEdgeIndicesByStepAmount 返回的可达到的最小值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] += 1
                    
                    flag = True
                    
                elif key == c4d.KEY_LEFT:
                    print "{0}".format("Ctrl+Left")
                    
                    stepAmount = 0
                    edgeIndices = None
                    direction, stepDistance = edge.GetUpDownStepDistance()
                    if stepDistance != 0:
                        lastStepAmount = 0
                        stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(lastStepAmount + 1)
                        # 
                        while stepAmount != lastStepAmount:
                            lastStepAmount = stepAmount
                            stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(lastStepAmount + 1)
                    else:
                        direction, stepDistance = edge.GetLeftRightStepDistance()
                        if stepDistance != 0:
                            lastStepAmount = 0
                            stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(lastStepAmount + 1)
                            # 
                            while stepAmount != lastStepAmount:
                                lastStepAmount = stepAmount
                                stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(lastStepAmount + 1)
                    
                    if edgeIndices:
                        print "ori:", originEdgeIndices, "direction:", StringHelper.DirectionToString(direction), " edges:", edgeIndices
                        edge.SetSelectedEdgeIndices(edgeIndices)
                        # 修改为 GetUpDownEdgeIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] = 0
                        
                    flag = True
                    
                elif key == c4d.KEY_RIGHT: # 同c4d.KEY_LEFT
                    print "{0}".format("Ctrl+Right")
                    
                    stepAmount = 0
                    edgeIndices = None
                    direction, stepDistance = edge.GetUpDownStepDistance()
                    if stepDistance != 0:
                        lastStepAmount = 0
                        stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(lastStepAmount + 1)
                        # 
                        while stepAmount != lastStepAmount:
                            lastStepAmount = stepAmount
                            stepAmount, edgeIndices = edge.GetUpDownEdgeIndicesByStepAmount(lastStepAmount + 1)
                    else:
                        direction, stepDistance = edge.GetLeftRightStepDistance()
                        if stepDistance != 0:
                            lastStepAmount = 0
                            stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(lastStepAmount + 1)
                            # 
                            while stepAmount != lastStepAmount:
                                lastStepAmount = stepAmount
                                stepAmount, edgeIndices = edge.GetLeftRightEdgeIndicesByStepAmount(lastStepAmount + 1)
                    
                    if edgeIndices:
                        print "ori:", originEdgeIndices, "direction:", StringHelper.DirectionToString(direction), " edges:", edgeIndices
                        edge.SetSelectedEdgeIndices(edgeIndices)
                        # 修改为 GetUpDownEdgeIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] = 0
                        
                    flag = True
                    
                elif key == ord('L'): # ascii转换
                    print "{0}".format("Ctrl+L --- Loop in other direction")
                    
                    edgeIndices = None
                    direction, stepDistance = edge.GetUpDownStepDistance()
                    #print "SD:", stepDistance
                    if stepDistance != 0: # 原方向为UpDown，则other direction = loop
                        edgeIndices = edge.GetUpDownLoopEdgeIndices()
                    else: # 原方向为LeftRight，则other direction = loop
                        direction, stepDistance = edge.GetLeftRightStepDistance()
                        if stepDistance != 0:
                            edgeIndices = edge.GetLeftRightLoopEdgeIndices()
                    
                    if edgeIndices:
                        print "ori:", originEdgeIndices, "direction:", StringHelper.DirectionToString(direction), " edges:", edgeIndices
                        edge.SetSelectedEdgeIndices(edgeIndices)
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] = 0
                    
                    flag = True
            
            # 设置flag主要是为nbr.Flush()。nbr不Flush，当op改变后，nbr会Exception
            if flag:            
                c4d.DrawViews(c4d.DA_ONLY_ACTIVE_VIEW|c4d.DA_NO_THREAD|c4d.DA_NO_ANIMATION) # 界面更新
                nbr.Flush()
                return True
                
        print "key {0} pressed.".format(cstr)
        # False时，交由c4d处理。缺点：会切换当前plugin到其它工具
        # True时，可以保证工具不会切换
        return False
                
    def ShowPopupMenu(self, bd, mx, my):    
        menu = c4d.BaseContainer()
        menu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_MENU1, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_MENU1))
        menu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_MENU2, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_MENU2))
        
        menu.InsData(0, '') # separator
        
        submenu = c4d.BaseContainer()
        submenu.InsData(1, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_MENU3)) # 子菜单的父级菜单项
        submenu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU1, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU1))
        submenu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU2, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU2))        
        submenu.InsData(0, '') # separator
        submenu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_SUBMENU3, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_SUBMENU3))
        menu.SetContainer(IDM_SIMPLELOOPSELECTIONEDGE_MENU3, submenu) # 添加子菜单到主菜单
        
        menu.InsData(0, '') # separator
        
        menu.InsData(IDM_SIMPLELOOPSELECTIONEDGE_MENU4, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_MENU4))        

        # 弹出菜单
        result = gui.ShowPopupDialog(None, menu, mx, my) # result是点击的菜单ID
        print result
    
    """
    只能捕捉到 Message: 1001090 - {'h': 24, 'bmp': <c4d.bitmaps.BaseBitmap object at 0x0000000016B8C850>, 'flags': 0, 'w': 24, 'y': 0, 'x': 0, 'filled': False}
    len(data) = 0
    """
    def Message(self, doc, data, type, t_data):
        # print "Message: {0} - {1}, {2}".format(type, data, len(data))
        # for index, value in data:
            # print "----Index: %i, Value: %s" % (index, str(value))
        
        #return super(SimpleLoopSelectionEdge, self).Message(doc, data, type, t_data) # err
        return True
    
    """
    切换op时，会只选择一个，而不是当前的选择?
    -------------------------------------------
    MouseInput只能捕捉 BFM_INPUT_MOUSELEFT，即点击click
    而无法捕捉 BFM_INPUT_MOUSEMOVE / BFM_INPUT_MOUSERIGHT
    msg 相当于 MouseDrag.channels
    """
    def MouseInput(self, doc, data, bd, win, msg):        
        # MouseInput 传入的是 FrameScreen Coor.
        sx, sy = msg[c4d.BFM_INPUT_X], msg[c4d.BFM_INPUT_Y]
        # 鼠标坐标切换 FrameScreenToWindow
        mx, my = BaseDrawHelper.FrameScreenToWindow(bd, sx, sy)
        
        device = 0
        #if msg[c4d.BFM_INPUT_CHANNEL]==c4d.BFM_INPUT_MOUSEMOVE: # mouse move无效?
            #print "BFM_INPUT_MOUSEMOVE {0}, {1}".format(mx, my)
            # pass
        if msg[c4d.BFM_INPUT_CHANNEL]==c4d.BFM_INPUT_MOUSELEFT: # 左键
            device = c4d.KEY_MLEFT
            #self.ShowPopupMenu(bd, mx, my)
        elif msg[c4d.BFM_INPUT_CHANNEL]==c4d.BFM_INPUT_MOUSERIGHT: # 右键无效?，弹出菜单
            print "KEY_MRIGHT {0}, {1}".format(mx, my)
            device = c4d.KEY_MRIGHT
            #self.ShowPopupMenu(bd, mx, my)
            return True
        else:  # 中键等，不处理
            return True
        
        # -------- Mouse click: BFM_INPUT_MOUSELEFT 时，+/- edges
        op = doc.GetActiveObject()
        if op and op.IsInstanceOf(c4d.Opolygon):                
            #利用 self.parameters 初始化已有的参数（不严谨，切换op时其实已经无效）
            if op == self.parameters["OP"]:
                pass
            else:
                self.parameters["LastOriginEdgeIndex"] = -1

            nbr = c4d.utils.Neighbor()
            nbr.Init(op)
            edge = EdgeHelper(op, nbr)
            originEdgeIndices = []
            
            # ?未解决：切换op时，以当前选择的最后2个为origin（多个选择时，未/无需细分确认最后）
            selectedEdgeIndices = edge.GetSelectedEdgeIndices()
            if selectedEdgeIndices:
                if len(selectedEdgeIndices) >= 2:
                    originEdgeIndices.extend(selectedEdgeIndices[-2:])
                elif len(selectedEdgeIndices) == 1:
                    originEdgeIndices.append(selectedEdgeIndices[0])


            edgeIndex = edge.GetEdgeIndexUnderMouse(doc, bd, sx, sy)
            if edgeIndex != -1:
                originIndex = ArrayHelper.GetIndex(originEdgeIndices, edgeIndex)
                # Ctrl/Shift+click 切换，如果超过两个，则只保留最后选的那个和新选的
                if (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QCTRL) or (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QSHIFT):
                    if originIndex != -1: # 当前已作为origin，则从origin中删除
                        del originEdgeIndices[originIndex]
                        
                        if len(originEdgeIndices) != 0: # 删除当前之后，可能无已选择
                            self.parameters["LastOriginEdgeIndex"] = originEdgeIndices[0]
                        else:
                            self.parameters["LastOriginEdgeIndex"] = -1
                    else: # 加新，去旧（只保留最后选的那个）
                        originIndex2 = ArrayHelper.GetIndex(originEdgeIndices, self.parameters["LastOriginEdgeIndex"])
                        if originIndex2 != -1 and len(originEdgeIndices) == 2: # 当前已作为origin，则从origin2中删除不是最后的那个
                            if originIndex2 == 0:
                                del originEdgeIndices[1]
                            elif originIndex2 == 1:
                                del originEdgeIndices[0]
                                
                        elif originIndex2 == -1 and len(originEdgeIndices) == 2: # 无法判断时，删除[0]
                            del originEdgeIndices[0]
                        
                        originEdgeIndices.append(edgeIndex)
                        self.parameters["LastOriginEdgeIndex"] = edgeIndex
                else: # 单纯click，只选择当前
                    originEdgeIndices = [edgeIndex]
                    self.parameters["LastOriginEdgeIndex"] = edgeIndex
                
                # 设置origin & selected
                edge.SetOriginEdgeIndices(originEdgeIndices)
                edge.SetSelectedEdgeIndices(originEdgeIndices)                         
                    
                # 保存参数
                self.parameters["OP"] = op
                self.parameters["OriginEdgeIndices"] = edge.GetOriginEdgeIndices()
                self.parameters["StepAmount"] = 0 # 每次选择完 origin，则重新计算 stepAmount
                
                c4d.DrawViews(c4d.DA_ONLY_ACTIVE_VIEW|c4d.DA_NO_THREAD|c4d.DA_NO_ANIMATION) # 界面更新
                
            nbr.Flush()
            
        return True
    
    """
    无法捕捉BFM_INPUT_MOUSEMOVE，只发生在Alt按下并拖动时
    """
    def Draw(self, doc, data, bd, bh, bt, flags):       
        """
        # liquid brush style标志
        # if flags & c4d.TOOLDRAWFLAGS_HIGHLIGHT:
            # #Draw your stuff inside the highlight plane
            # p = [c4d.Vector(0,0,0), c4d.Vector(100,0,0), c4d.Vector(50,100,0)]
            # f = [c4d.Vector(1,0,0), c4d.Vector(1,0,0), c4d.Vector(1,0,0)]
        # elif flags & c4d.TOOLDRAWFLAGS_INVERSE_Z: # 半透明
            # # Draw your stuff into the active plane - invisible Z
            # p = [c4d.Vector(0,0,0), c4d.Vector(100,0,0), c4d.Vector(50,-100,0)]
            # f = [c4d.Vector(0,0,1), c4d.Vector(0,0,1), c4d.Vector(0,0,1)]
        # elif not flags:
            # # Draw your stuff into the active plane - visible Z
            # p = [c4d.Vector(0,0,0), c4d.Vector(-100,0,0), c4d.Vector(-50,100,0)]
            # f = [c4d.Vector(0,1,0), c4d.Vector(0,1,0), c4d.Vector(0,1,0)]
            
        # bd.DrawPolygon(p, f)
        """
        
        # 获取鼠标位置
        state = c4d.BaseContainer()
        if gui.GetInputState(c4d.BFM_INPUT_MOUSE, c4d.BFM_INPUT_MOUSELEFT, state):
            if state.GetInt32(c4d.BFM_INPUT_VALUE)==0: pass
            mx = state.GetInt32(c4d.BFM_INPUT_X)
            my = state.GetInt32(c4d.BFM_INPUT_Y)
            
            # 鼠标坐标切换
            sx, sy = BaseDrawHelper.WindowToFrameScreen(bd, mx, my)
        
        return c4d.TOOLDRAW_HANDLES | c4d.TOOLDRAW_AXIS    
         
    """
    代替 MouseMove：排除 c4d.BFM_CURSORINFO_REMOVE 之后，剩下的就是相当于 BFM_INPUT_MOUSEMOVE
    无法捕捉 BFM_INPUT_MOUSERIGHT
    不支持bd.Draw?
    data 0长度
    """
    def GetCursorInfo(self, doc, data, bd, x, y, bc):        
        if bc.GetId() == c4d.BFM_CURSORINFO_REMOVE: # BFM_CURSORINFO_REMOVE发生在鼠标移出userarea即绘图区的时候
            return True

        state = c4d.BaseContainer()
        if gui.GetInputState(c4d.BFM_INPUT_MOUSE, c4d.BFM_INPUT_MOUSELEFT, state):
            if state.GetInt32(c4d.BFM_INPUT_VALUE)==0: pass
            # 鼠标坐标切换 WindowToFrameScreen
            # GetCursorInfo 得到的是 FrameScreen Coor.
            # GetInputState 得到的是 Window Coor.
            mx, my = state.GetInt32(c4d.BFM_INPUT_X), state.GetInt32(c4d.BFM_INPUT_Y)
            #print x, ":", mx-left-x, " ;", y, ":", my-top+22-y
            
            op = doc.GetActiveObject()
            if op and op.IsInstanceOf(c4d.Opolygon):
                nbr = None
                edge = None
                    
                nbr = c4d.utils.Neighbor()
                nbr.Init(op)
                edge = EdgeHelper(op, nbr)
                    
                edgeIndex = edge.GetEdgeIndexUnderMouse(doc, bd, x, y)
                if edgeIndex != -1:
                    edge.SetEdgeIndex(edgeIndex)
                    #print "edge:", edge
                    
                    # --------------------------------
                    # originEdgeIndex1, originEdgeIndex2 = 407, 359
                    
                    # edge2 = EdgeHelper(op, nbr)
                    # edge2.SetEdgeIndex(originEdgeIndex1)
                    # rightEdge = edge2.GetRightNearbyEdge()
                    # print "|---right:", rightEdge
                    # if rightEdge and rightEdge.edgeIndex != -1:
                        # edge.SetOriginEdgeIndices([originEdgeIndex1, rightEdge.edgeIndex])
                    
                    # edge2 = EdgeHelper(op, nbr)
                    # edge2.SetEdgeIndex(originEdgeIndex2)
                    # rightEdge2 = edge2.GetRightNearbyEdge()
                    # print "|---right:", rightEdge
                    
                    # edge.SetSelectedEdgeIndices([originEdgeIndex1, originEdgeIndex2, rightEdge.edgeIndex, rightEdge2.edgeIndex])
                    
                    
                    # --------------------------------
                    
                    
                    # ======= 画高亮线 ========
                    bh = c4d.plugins.BaseDrawHelp(bd, doc)
                    if bh and doc.GetMode() == c4d.Medges: # edgemode
                        #bd.SetMatrix_Matrix(op, bh.GetMg()) # 坐标切换无效?
                        bd.SetPointSize(100) # 高亮线粗细
                        bd.SetPen(c4d.GetViewColor(c4d.VIEWCOLOR_SELECTION_PREVIEW))
                        #bd.SetPen(c4d.GetViewColor(c4d.VIEWCOLOR_ACTIVEPOINT))
                        
                        p1pos, p2pos = edge.GetPointsPosition() # local
                        p1pos, p2pos = p1pos * op.GetMg(), p2pos * op.GetMg() # local转换成global
                        #bd.DrawLine(p1pos, p2pos, c4d.NOCLIP_D) # DrawLine无效?
                        
                        p1pos2D, p2pos2D = bd.WS(p1pos), bd.WS(p2pos)
                        bd.DrawLine2D(p1pos2D, p2pos2D) # 使用DrawLine2D可以（只有边界有效?）
                        
                        c4d.DrawViews(c4d.DA_ONLY_ACTIVE_VIEW|c4d.DA_NO_THREAD|c4d.DA_NO_ANIMATION) # 界面更新
                    # ======= end: 画高亮线 ========
                
                nbr.Flush()
                
        bc.SetString(c4d.RESULT_BUBBLEHELP, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONEDGE_TOOLTIP))
        #bc.SetLong(c4d.RESULT_CURSOR, c4d.MOUSE_POINT_HAND) # 设置鼠标样式
        return False

    # 每次都生成一个新实例，并参数同步（引用）
    def AllocSubDialog(self, bc):
        #return SimpleLoopSelectionEdgeDialog()
        return SimpleLoopSelectionEdgeDialog(self.parameters)


if __name__ == "__main__":
    bmp = bitmaps.BaseBitmap()
    dir, file = os.path.split(__file__)
    fn = os.path.join(dir, "res", "tsimpleloopselectionedge.tif")
    bmp.InitWith(fn)
    plugins.RegisterToolPlugin(id=PLUGIN_ID, str="Simple Loop Selection Edge",
                                info=0, icon=bmp, 
                                help="Simple Loop Selection Edge help",
                                dat=SimpleLoopSelectionEdge())

                                
                                