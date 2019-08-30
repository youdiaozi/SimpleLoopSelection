import c4d
import os
import sys

from c4d import gui, plugins, bitmaps

#be sure to use a unique ID obtained from https://plugincafe.maxon.net/c4dpluginid_cp
PLUGIN_ID = 1053306

#for GeLoadString（IDS IDM 无法以c4d.的形式调用?）
# Control IDs (1001+)
ID_SIMPLELOOPSELECTIONPOLYGON_TIPS1                    = 1201
ID_SIMPLELOOPSELECTIONPOLYGON_TIPS2                    = 1202
ID_SIMPLELOOPSELECTIONPOLYGON_TIPS3                    = 1203
ID_SIMPLELOOPSELECTIONPOLYGON_TIPS4                    = 1204
                                                
# Control String IDs (50000+)                      
IDS_SIMPLELOOPSELECTIONPOLYGON_TOOLTIP                 = 50200
IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS1                   = 50201
IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS2                   = 50202
IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS3                   = 50203
IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS4                   = 50204

DIRECTION_NONE = -1
DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3
DIRECTION_LOOP = 4

SIDE_NONE = -1  
SIDE_0 = 0
SIDE_1 = 1
SIDE_2 = 2
SIDE_3 = 3

"""
怎么变换鼠标图标?
怎么加粗DrawLine2D，或者变换坐标为直接3D?
"""

class StringHelper():
    @staticmethod
    def DirectionToString(direction):
        strings = { DIRECTION_NONE: "DIRECTION_NONE", DIRECTION_UP: "DIRECTION_UP", DIRECTION_DOWN: "DIRECTION_DOWN", DIRECTION_LEFT: "DIRECTION_LEFT", DIRECTION_RIGHT: "DIRECTION_RIGHT", DIRECTION_LOOP: "DIRECTION_LOOP" }
        return strings[direction]
        
    @staticmethod
    def SideToString(side):
        strings = { SIDE_NONE: "SIDE_NONE", SIDE_0: "SIDE_0", SIDE_1: "SIDE_1", SIDE_2: "SIDE_2", SIDE_3: "SIDE_3" }
        return strings[side]

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


class PolygonHelper():
    nbr = None
    op = None
    
    _polygonIndex = -1
    _a = -1
    _b = -1
    _c = -1
    _d = -1
    _originPolygonIndex1 = -1 # origin selected polygon index(greater)
    _originPolygonIndex2 = -1 # origin selected polygon index(smaller)
        
    def __init__(self, op, nbr):
        self.op = op
        self.nbr = nbr
        
    def __eq__(self, other):
        # and self.op == other.op and self.nbr == other.nbr
        return self._polygonIndex == other._polygonIndex
        
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __str__(self):
        a, b, c, d = self.GetPointIndices()
        msg = "{0} --- a, b, c, d: {1}, {2}, {3}, {4}".format(self.polygonIndex, a, b, c, d)
        return msg
        
    @property
    def polygonIndex(self):
        return self._polygonIndex
        
    @property
    def a(self):
        return self._a
        
    @property
    def b(self):
        return self._b
    
    @property
    def c(self):
        return self._c
        
    @property
    def d(self):
        return self._d
        
    """
    计算鼠标位置下的polygonIndex（已转换成op/nbr的格式）
    ------------------------------------
    viewportSelect.GetPixelInfoPolygon得到的值是info["i"] = 4*polygonIndex+side，即0-1-2-3，4-5-6-7，8-9-10-11
    而op、nbr的所有计算，如GetSelectedPolygons、GetPolygonCount、GetPolygonPolygons、GetPolygonInfo等，都是按0-1-2-3，(2)-4-5-6，(5)-7-8-9的形式计算
    """
    def GetPolygonIndexUnderMouse(self, doc, bd, sx, sy):
        if not self.op.IsInstanceOf(c4d.Opolygon): return -1 # 未C的对象会引发 ViewportSelect.Init 的 Exception

        try:
            width, height = BaseDrawHelper.GetFrameWidthHeight(bd)
            
            viewportSelect = c4d.utils.ViewportSelect()
            viewportSelect.Init(width, height, bd, [self.op], c4d.Mpolyedgepoint, True, c4d.VIEWPORTSELECTFLAGS_IGNORE_HIDDEN_SEL)
            
            #info = viewportSelect.GetPixelInfoPolygon(sx, sy) # 难以选择上
            info = viewportSelect.GetNearestPolygon(self.op, sx, sy) # GetNearestPolygon 更容易选择
            viewportSelect.ClearPixelInfo(sx, sy, c4d.VIEWPORT_CLEAR_POLYGON)
            
            if info: 
                polygonIndex = info["i"]
                return polygonIndex
        except Exception, e:
            print "err:", e
            return -1
            
        return -1

    """
    由polygonIndex计算a b c d
    """
    def SetPolygonIndex(self, value):
        allpolygons = self.op.GetAllPolygons()
        if value >= 0 and value < len(allpolygons):
            i = value
            #print "value: ", value, " a, b, c, d:", allpolygons[i].a, allpolygons[i].b, allpolygons[i].c, allpolygons[i].d            
            if allpolygons[i].c != allpolygons[i].d: # 去掉三角面等                
                self._polygonIndex = i
                self._a, self._b, self._c, self._d = allpolygons[i].a, allpolygons[i].b, allpolygons[i].c, allpolygons[i].d
                return
                
        self._polygonIndex = -1
    
    """
    计算a, b, c, d(index)
    """
    def GetPointIndices(self):
        if self.polygonIndex == -1:
            return -1, -1, -1, -1
            
        return self.a, self.b, self.c, self.d
        
    def GetPointsPosition(self):
        if self.polygonIndex != -1:
            pointsPosition = []
            pointsPosition.append(self.op.GetPoint(self.a))
            pointsPosition.append(self.op.GetPoint(self.b))
            pointsPosition.append(self.op.GetPoint(self.c))
            pointsPosition.append(self.op.GetPoint(self.d))
            return pointsPosition
            
        return None
        
    """
    @for 已选择的polygon索引数组（重叠的不算）
    @remark 总polygon数：nbr.GetPolygonCount() # 重叠的不算
            已选择的polygon数：polygons.GetCount()
    """
    def GetSelectedPolygonIndices(self):
        #polygons = c4d.BaseSelect()
        polygons = self.op.GetPolygonS()
                   
        polygonIndices = []
        for index in xrange(self.op.GetPolygonCount()):
            if polygons.IsSelected(index):
                polygonIndices.append(index)
                
        return polygonIndices
    
    """
    默认：False替换
    isAdd = True，则添加；False，则替换
    """
    def SetSelectedPolygonIndices(self, polygonIndices, isAdd=False):
        indices = []
        polygons = c4d.BaseSelect()
        if isAdd:
            polygons = self.op.GetPolygonS()
            indices.extend(self.GetSelectedPolygonIndices())
            indices.extend(polygonIndices)
        else:
            polygons = self.op.GetPolygonS()
            polygons.DeselectAll()
            
        for polygonIndex in polygonIndices:
            polygons.Select(polygonIndex)
        
        return indices
                
    # ---------------- Up / Down -------------------
    # 大在前
    def GetOriginPolygonIndices(self):
        if self._originPolygonIndex2 == -1:
            if self._originPolygonIndex1 == -1:
                return []
            else:
                return [self._originPolygonIndex1]
        else:
            return [self._originPolygonIndex1, self._originPolygonIndex2]
    
    # 大在前
    def SetOriginPolygonIndices(self, originPolygonIndices):
        if not originPolygonIndices or len(originPolygonIndices) == 0:
            self._originPolygonIndex1, self._originPolygonIndex2 = -1, -1
        elif len(originPolygonIndices) == 1:
            self._originPolygonIndex1, self._originPolygonIndex2 = originPolygonIndices[0], -1
        elif len(originPolygonIndices) == 2:
            #self._originPolygonIndex1, self._originPolygonIndex2 = max(originPolygonIndices), min(originPolygonIndices)        
            originPolygonIndices.sort(reverse = True)
            self._originPolygonIndex1, self._originPolygonIndex2 = originPolygonIndices[0], originPolygonIndices[1]
        else:
            originPolygonIndices = originPolygonIndices[-2:]
            #self._originPolygonIndex1, self._originPolygonIndex2 = max(originPolygonIndices), min(originPolygonIndices)
            originPolygonIndices.sort(reverse = True)
            self._originPolygonIndex1, self._originPolygonIndex2 = originPolygonIndices[0], originPolygonIndices[1]
    
    def SwapEqual(self, a, b, p1, p2):
        return (a == p1 and b == p2) or (b == p1 and a == p2)     
    
    def GetOppositePolygon(self, p1, p2):
        if self.polygonIndex == -1 or p1 == -1 or p2 == -1:
            return None
            
        if self.c == self.d:
            return None # 三角面等
        
        oppositePolygonIndex = self.nbr.GetNeighbor(p1, p2, self.polygonIndex)
        if oppositePolygonIndex != -1:
            oppositePolygon = PolygonHelper(self.op, self.nbr)
            oppositePolygon.SetPolygonIndex(oppositePolygonIndex)
            
            if oppositePolygon.c == oppositePolygon.d:
                return None # 三角面等
            
            # side = -1
            # if self.SwapEqual(self.a, self.b, p1, p2):
                # side = 0
            # elif self.SwapEqual(self.b, self.c, p1, p2):
                # side = 1
            # elif self.SwapEqual(self.c, self.d, p1, p2):
                # side = 2
            # elif self.SwapEqual(self.d, self.a, p1, p2):
                # side = 3
                
            return oppositePolygon
            
        return None
    
    """
    a b边出发
    """
    def GetDirectionBySide(self, side):
        if side == 0:
            return DIRECTION_LEFT
        if side == 1:
            return DIRECTION_UP
        if side == 2:
            return DIRECTION_RIGHT
        if side == 3:
            return DIRECTION_DOWN
            
        return DIRECTION_NONE
    
    """
    跟edge不一样，polygon.direction是指由 startPolygon 出发时(a b)，所接应的 side
    side 同 direction 的对应：
        side = 0: DIRECTION_LEFT
        side = 1: DIRECTION_UP
        side = 2: DIRECTION_RIGHT
        side = 3: DIRECTION_DOWN
    """
    def GetUpDownStepDistance(self):
        originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
        
        startPolygon = PolygonHelper(self.op, self.nbr)
        startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
        endPolygon = PolygonHelper(self.op, self.nbr)
        endPolygon.SetPolygonIndex(originPolygonIndex1) # 起点1，polygonIndex大的边为up(start -> end)
               
        # stepDistance 指起点2到起点1的间隔polygon数（+1）
        stepDistance = [0]*4
        meetflag = [False]*4
        breakflag = [False]*4
        sideflag = [True]*4
        lastSide = SIDE_NONE
        lastStepDistance = sys.maxint
        # 以下计算主要是获取 meetflag 和 stepDistance 的值
        #print "|---start, end:", startPolygon, "/ ", endPolygon
        if startPolygon and endPolygon:            
            for side in xrange(4):
                stepDistance[side] = 0
                meetflag[side] = False
                breakflag[side] = False
                sideflag[side] = True
                startPolygon = PolygonHelper(self.op, self.nbr)
                startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
        
                while startPolygon and startPolygon.polygonIndex != -1:
                    if sideflag[side]:
                        sideflag[side] = False
                        startPoints = [startPolygon.a, startPolygon.b, startPolygon.c, startPolygon.d]
                        oppositePoints = [startPoints[(side)%4], startPoints[(side+1)%4]]
                    else:
                        oppositePoints = startPolygon.GetOppositePoints(startPolygon, oppositePoints)
                
                    oppositePolygon = startPolygon.GetOppositePolygon(oppositePoints[0], oppositePoints[1])
                    #print "|---oppo:", oppositePolygon
                    if oppositePolygon and oppositePolygon.polygonIndex != -1:
                        stepDistance[side] += 1
                        
                        # 遇到起点1，结束stepDistance计算
                        if oppositePolygon.polygonIndex == endPolygon.polygonIndex:
                            meetflag[side] = True
                            #print "meet:side:", side, "distance:", stepDistance[side]
                            if stepDistance[side] < lastStepDistance:
                                lastStepDistance = stepDistance[side]
                                lastSide = side
                            break
                            
                        # 遇到起点2（原自己），跳出无限循环，直接返回
                        if oppositePolygon.polygonIndex == originPolygonIndex2:
                            breakflag[side] = True
                            break
                            
                        startPolygon = oppositePolygon
                    else:
                        break
                        
                        
        if lastSide != SIDE_NONE:
            return lastSide, stepDistance[lastSide]
            
        return SIDE_NONE, 0
    
    def GetOppositePoints(self, polygon, points):
        pts = [polygon.a, polygon.b, polygon.c, polygon.d]
        return [pt for pt in pts if pt not in points]
        
    """
    获取downPolygons（按polygonIndex小的边向不是大的边的方向）
    """
    def GetDownPolygonIndices(self, side, stepDistance):
        if self._originPolygonIndex1 == -1 or self._originPolygonIndex2 == -1 or not (side in [SIDE_0, SIDE_1, SIDE_2, SIDE_3]):
            return None

        originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
        
        if stepDistance >= 1:
            upPolygonIndices = []
            
            startPolygon = PolygonHelper(self.op, self.nbr)
            startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
            endPolygon = PolygonHelper(self.op, self.nbr)
            endPolygon.SetPolygonIndex(originPolygonIndex1) # 起点1，polygonIndex大的边为up(start -> end)
            
            # stepDistance 指起点2到起点1的间隔polygon数（+1）
            #print "|---start, end:", startPolygon, "/ ", endPolygon
            if startPolygon and endPolygon:
                breakflag = False
                sideflag = True
                oppositePoints = []
                while startPolygon and startPolygon.polygonIndex != -1:
                    for st in xrange(stepDistance):
                        if sideflag:
                            sideflag = False
                            startPoints = [startPolygon.a, startPolygon.b, startPolygon.c, startPolygon.d]
                            oppositePoints = [startPoints[(side+2)%4], startPoints[(side+3)%4]]
                        else:
                            oppositePoints = self.GetOppositePoints(startPolygon, oppositePoints)
                        
                        oppositePolygon = startPolygon.GetOppositePolygon(oppositePoints[0], oppositePoints[1])
                        #print "|---oppo:", oppositePolygon
                        if oppositePolygon and oppositePolygon.polygonIndex != -1:
                            # 遇到起点2（原自己），跳出无限循环，直接返回
                            if oppositePolygon.polygonIndex == originPolygonIndex2:
                                breakflag = True
                                break # break for
                        else:
                            breakflag = True
                            break # break for
                        
                        startPolygon = oppositePolygon
                
                    if breakflag:
                        break # break while
                    
                    #print "|---start:", startPolygon
                    upPolygonIndices.append(startPolygon.polygonIndex)
            
            return upPolygonIndices
            
        # 没有找到
        return None
    
    """"
    获取upPolygons（按polygonIndex小的边向大的边的方向）
    -------------------------------------------
    简化计算，全部统一由起点2开始，各side方向都使用统一算法
    """
    def GetUpPolygonIndices(self, side, stepDistance):
        if self._originPolygonIndex1 == -1 or self._originPolygonIndex2 == -1 or not (side in [SIDE_0, SIDE_1, SIDE_2, SIDE_3]):
            return None

        originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
        
        if stepDistance >= 1:
            upPolygonIndices = []
            
            startPolygon = PolygonHelper(self.op, self.nbr)
            startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
            endPolygon = PolygonHelper(self.op, self.nbr)
            endPolygon.SetPolygonIndex(originPolygonIndex1) # 起点1，polygonIndex大的边为up(start -> end)
            
            # stepDistance 指起点2到起点1的间隔polygon数（+1）
            #print "|---start, end:", startPolygon, "/ ", endPolygon
            if startPolygon and endPolygon:
                breakflag = False
                sideflag = True
                oppositePoints = []
                while startPolygon and startPolygon.polygonIndex != -1:
                    for st in xrange(stepDistance):
                        if sideflag:
                            sideflag = False
                            startPoints = [startPolygon.a, startPolygon.b, startPolygon.c, startPolygon.d]
                            oppositePoints = [startPoints[(side)%4], startPoints[(side+1)%4]]
                        else:
                            oppositePoints = self.GetOppositePoints(startPolygon, oppositePoints)
                        
                        oppositePolygon = startPolygon.GetOppositePolygon(oppositePoints[0], oppositePoints[1])
                        #print "|---oppo:", oppositePolygon
                        if oppositePolygon and oppositePolygon.polygonIndex != -1:
                            # 遇到起点2（原自己），跳出无限循环，直接返回
                            if oppositePolygon.polygonIndex == originPolygonIndex2:
                                breakflag = True
                                break # break for
                        else:
                            breakflag = True
                            break # break for
                        
                        startPolygon = oppositePolygon
                
                    if breakflag:
                        break # break while
                    
                    #print "|---start:", startPolygon
                    upPolygonIndices.append(startPolygon.polygonIndex)
                
            if len(upPolygonIndices) >= 1:
                upPolygonIndices = upPolygonIndices[1:] # 为了计算方便，把起点1也算进去了，所以在最后结果里要除出来。
            
            return upPolygonIndices
            
        # 没有找到
        return None

    """    
    返回：tuple(stepAmount, polygonIndices)，方便stepAmount达到应该的最大值时-1操作
    ----------------------------
    stepAmount可以任意整数，正数表示UpPolygons，0表示origin，-1表示起点2（polygonIndex小的边），负数表示DownPolygons
    当正数超过UpPolygons数时，加上DownPolygons；当负数超过DownPolygons数时，加上UpPolygons。
    """
    def GetUpDownPolygonIndicesByStepAmount(self, stepAmount):
        polygonIndices = []
        originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2        
        
        
        side, stepDistance = self.GetUpDownStepDistance()
        print "Side:", side
        if stepDistance == 0: # 不在一个方向上
            return 0, None
        
        print "Want StepAmount:", stepAmount # 这个值up最大时可能会+1，down最小时可能会-1
        
        if stepAmount == -1: # 返回起点2
            polygonIndices.append(originPolygonIndex2)
        elif stepAmount == 0: # 没有+/-时，返回origin
            polygonIndices.extend([originPolygonIndex2, originPolygonIndex1])
        else:
            upPolygonIndices = self.GetUpPolygonIndices(side, stepDistance)
            #print "upPolygonIndices:", upPolygonIndices
            if not upPolygonIndices:
                upPolygonIndices = []
            downPolygonIndices = self.GetDownPolygonIndices(side, stepDistance)
            if not downPolygonIndices:
                downPolygonIndices = []
            print "up:", upPolygonIndices, " down:", downPolygonIndices
            
            if stepAmount > 0: # origin2/1 + 部分/全部upPolygonIndices + 部分downPolygonIndices
                # 去除down中up有的元素，防止同一个polygonIndex重复添加
                downPolygonIndices = ArrayHelper.RemoveSame(downPolygonIndices, upPolygonIndices)
                
                # 超过可达到的最大 stepAmount，则保留参数
                stepAmount = min(stepAmount, len(upPolygonIndices) + len(downPolygonIndices))
                
                allIndices = [originPolygonIndex2, originPolygonIndex1] # 加上origin
                allIndices.extend(upPolygonIndices)
                allIndices.extend(downPolygonIndices)
                
                polygonIndices = allIndices[:stepAmount+2]
                    
            else: # stepAmount < -1 --> origin2 + 部分/全部downPolygonIndices + origin1 + 部分upPolygonIndices 
                # 去除up中down有的元素，防止同一个polygonIndex重复添加
                upPolygonIndices = ArrayHelper.RemoveSame(upPolygonIndices, downPolygonIndices)
                
                # 超过可达到的最小 stepAmount，则保留参数
                stepAmount = max(stepAmount, -(len(upPolygonIndices) + len(downPolygonIndices) + 2))
                
                allIndices = [originPolygonIndex2] # 加上origin2                
                allIndices.extend(downPolygonIndices)
                allIndices.append(originPolygonIndex1) # 加上origin1                
                allIndices.extend(upPolygonIndices)
                
                polygonIndices = allIndices[:-stepAmount]
                    
        return stepAmount, polygonIndices
            
    # ---------------- end: Up / Down -------------------
        
    # ---------------- loop in other direction -------------------    
    
    """
    因为side只对origin2有效，所以在origin1时，需要使用另外的算法
    """
    def GetRightNearbyPolygon(self, side, isOrigin2=True):
        allpolygons = self.op.GetAllPolygons()
        allpoints = [self.a, self.b, self.c, self.d]
        print "isOrigin2:", isOrigin2
        if isOrigin2:
            # side+1即rightNearby
            rightNearbyPoints = [allpoints[(side-2)%4], allpoints[(side-1)%4]]
            rightNearbyPolygon = self.GetOppositePolygon(rightNearbyPoints[0], rightNearbyPoints[1])
            if rightNearbyPolygon and rightNearbyPolygon.polygonIndex != -1:
                return rightNearbyPolygon
        else:
            originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
            
            startPolygon = PolygonHelper(self.op, self.nbr)
            startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
            endPolygon = PolygonHelper(self.op, self.nbr)
            endPolygon.SetPolygonIndex(originPolygonIndex1) # 起点1，polygonIndex大的边为up(start -> end)
                   
            # stepDistance 指起点2到起点1的间隔polygon数（+1）
            lastSide = SIDE_NONE
            lastStepDistance = sys.maxint
            # 以下计算主要是获取 meetflag 和 stepDistance 的值
            #print "|---start, end:", startPolygon, "/ ", endPolygon
            if startPolygon and endPolygon:
                stepDistance = 0
                meetflag = False
                breakflag = False
                sideflag = True
                oppositePoints = []
                startPolygon = PolygonHelper(self.op, self.nbr)
                startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
                print "start, end:", startPolygon.polygonIndex, endPolygon.polygonIndex
                while startPolygon and startPolygon.polygonIndex != -1:
                    if sideflag:
                        sideflag = False
                        startPoints = [startPolygon.a, startPolygon.b, startPolygon.c, startPolygon.d]
                        oppositePoints = [startPoints[(side)%4], startPoints[(side+1)%4]]
                    else:
                        oppositePoints = startPolygon.GetOppositePoints(startPolygon, oppositePoints)
                
                    oppositePolygon = startPolygon.GetOppositePolygon(oppositePoints[0], oppositePoints[1])
                    print "|---oppo:", oppositePolygon
                    if oppositePolygon and oppositePolygon.polygonIndex != -1:
                        stepDistance += 1
                        
                        # 遇到起点1，结束stepDistance计算
                        if oppositePolygon.polygonIndex == endPolygon.polygonIndex:
                            meetflag = True
                            break
                            
                        # 遇到起点2（原自己），跳出无限循环，直接返回
                        if oppositePolygon.polygonIndex == originPolygonIndex2:
                            breakflag = True
                            break
                            
                        startPolygon = oppositePolygon
                    else:
                        break                 
                
                # 遇到自己，则算出origin1的真正的side
                if meetflag:
                    print "meet"
                    realside = -1
                    for s in xrange(4):
                        if self.SwapEqual(allpoints[(s)%4], allpoints[(s+1)%4], oppositePoints[0], oppositePoints[1]):
                            realside = s
                            break
                            
                    if realside != -1:
                        # side+1即rightNearby
                        rightNearbyPoints = [allpoints[(realside-1)%4], allpoints[(realside)%4]]
                        rightNearbyPolygon = self.GetOppositePolygon(rightNearbyPoints[0], rightNearbyPoints[1])
                        if rightNearbyPolygon and rightNearbyPolygon.polygonIndex != -1:
                            print "|---right:", rightNearbyPolygon
                            return rightNearbyPolygon
                
            return None
            
    """
    因为side只对origin2有效，所以在origin1时，需要使用另外的算法
    """
    def GetLeftNearbyPolygon(self, side, isOrigin2=True):
        allpolygons = self.op.GetAllPolygons()
        allpoints = [self.a, self.b, self.c, self.d]
        print "isOrigin2:", isOrigin2
        if isOrigin2:
            # side+1即leftNearby
            leftNearbyPoints = [allpoints[(side)%4], allpoints[(side+1)%4]]
            leftNearbyPolygon = self.GetOppositePolygon(leftNearbyPoints[0], leftNearbyPoints[1])
            if leftNearbyPolygon and leftNearbyPolygon.polygonIndex != -1:
                return leftNearbyPolygon
        else:
            originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
            
            startPolygon = PolygonHelper(self.op, self.nbr)
            startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
            endPolygon = PolygonHelper(self.op, self.nbr)
            endPolygon.SetPolygonIndex(originPolygonIndex1) # 起点1，polygonIndex大的边为up(start -> end)
                   
            # stepDistance 指起点2到起点1的间隔polygon数（+1）
            lastSide = SIDE_NONE
            lastStepDistance = sys.maxint
            # 以下计算主要是获取 meetflag 和 stepDistance 的值
            #print "|---start, end:", startPolygon, "/ ", endPolygon
            if startPolygon and endPolygon:
                stepDistance = 0
                meetflag = False
                breakflag = False
                sideflag = True
                oppositePoints = []
                startPolygon = PolygonHelper(self.op, self.nbr)
                startPolygon.SetPolygonIndex(originPolygonIndex2)  # 起点2，polygonIndex小的边
                print "start, end:", startPolygon.polygonIndex, endPolygon.polygonIndex
                while startPolygon and startPolygon.polygonIndex != -1:
                    if sideflag:
                        sideflag = False
                        startPoints = [startPolygon.a, startPolygon.b, startPolygon.c, startPolygon.d]
                        oppositePoints = [startPoints[(side)%4], startPoints[(side+1)%4]]
                    else:
                        oppositePoints = startPolygon.GetOppositePoints(startPolygon, oppositePoints)
                
                    oppositePolygon = startPolygon.GetOppositePolygon(oppositePoints[0], oppositePoints[1])
                    print "|---oppo:", oppositePolygon
                    if oppositePolygon and oppositePolygon.polygonIndex != -1:
                        stepDistance += 1
                        
                        # 遇到起点1，结束stepDistance计算
                        if oppositePolygon.polygonIndex == endPolygon.polygonIndex:
                            meetflag = True
                            break
                            
                        # 遇到起点2（原自己），跳出无限循环，直接返回
                        if oppositePolygon.polygonIndex == originPolygonIndex2:
                            breakflag = True
                            break
                            
                        startPolygon = oppositePolygon
                    else:
                        break                 
                
                # 遇到自己，则算出origin1的真正的side
                if meetflag:
                    print "meet"
                    realside = -1
                    for s in xrange(4):
                        if self.SwapEqual(allpoints[(s)%4], allpoints[(s+1)%4], oppositePoints[0], oppositePoints[1]):
                            realside = s
                            break
                            
                    if realside != -1:
                        # side+1即leftNearby
                        leftNearbyPoints = [allpoints[(realside+1)%4], allpoints[(realside+2)%4]]
                        leftNearbyPolygon = self.GetOppositePolygon(leftNearbyPoints[0], leftNearbyPoints[1])
                        if leftNearbyPolygon and leftNearbyPolygon.polygonIndex != -1:
                            print "|---left:", leftNearbyPolygon
                            return leftNearbyPolygon
                
            return None

        
    """
    UpDownLoop 即 LeftRightPolygons
    """
    def GetUpDownLoopPolygonIndices(self, side):
        originPolygonIndex1, originPolygonIndex2 = self._originPolygonIndex1, self._originPolygonIndex2
        
        allIndices = []
        stepAmount = 1000
        
        #print "O1:O2:", originPolygonIndex1, originPolygonIndex2
        # origin1
        polygon = PolygonHelper(self.op, self.nbr)
        polygon.SetOriginPolygonIndices(self.GetOriginPolygonIndices())
        polygon.SetPolygonIndex(originPolygonIndex1)
        tempOrigin2 = polygon.GetRightNearbyPolygon(side, False)
        if not tempOrigin2 or tempOrigin2.polygonIndex == -1:
            tempOrigin2 = polygon.GetLeftNearbyPolygon(side, False)
        
        if tempOrigin2 and tempOrigin2.polygonIndex != -1:
            polygon.SetOriginPolygonIndices([originPolygonIndex1, tempOrigin2.polygonIndex])
            side, stepDistance = polygon.GetUpDownStepDistance()
            stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(stepAmount)
            allIndices.extend(polygonIndices)
        
        # origin2
        polygon = PolygonHelper(self.op, self.nbr)
        polygon.SetPolygonIndex(originPolygonIndex2)
        tempOrigin2 = polygon.GetRightNearbyPolygon(side)
        if not tempOrigin2 or tempOrigin2.polygonIndex == -1:
            tempOrigin2 = polygon.GetLeftNearbyPolygon(side)
        
        if tempOrigin2 and tempOrigin2.polygonIndex != -1:
            polygon.SetOriginPolygonIndices([originPolygonIndex2, tempOrigin2.polygonIndex])
            side, stepDistance = polygon.GetUpDownStepDistance()
            stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(stepAmount)
            allIndices.extend(polygonIndices)
        
        return allIndices
    
    # ---------------- end: loop in other direction -------------------    

class SimpleLoopSelectionPolygonDialog(gui.SubDialog):
    parameters = None

    """"
    接收 ToolData 参数，引用方式同步
    """
    def __init__(self, arg):
        self.parameters = arg

    def CreateLayout(self):        
        # ========== 文字提示 ==========
        self.GroupBegin(id=1000, flags=c4d.BFH_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(10, 0, 10, 0)
        
        tipsText1 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS1)
        self.tips1 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONPOLYGON_TIPS1, flags=c4d.BFH_MASK, name=tipsText1, borderstyle=c4d.BORDER_NONE)
        
        tipsText2 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS2)
        self.tips2 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONPOLYGON_TIPS2, flags=c4d.BFH_MASK, name=tipsText2, borderstyle=c4d.BORDER_NONE)
        
        tipsText3 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS3)
        self.tips3 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONPOLYGON_TIPS3, flags=c4d.BFH_MASK, name=tipsText3, borderstyle=c4d.BORDER_NONE)
        
        tipsText4 = plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONPOLYGON_TIPS4)
        self.tips4 = self.AddStaticText(id=ID_SIMPLELOOPSELECTIONPOLYGON_TIPS4, flags=c4d.BFH_MASK, name=tipsText4, borderstyle=c4d.BORDER_NONE)
        
        self.GroupEnd()
        # ========== end: 文字提示 ==========
        
        return True

    def Command(self, id, msg):
        # if id == SIMPLELOOPSELECTIONPOLYGON_BUTTON:
            # pass
            
        return True
        
class SimpleLoopSelectionPolygon(plugins.ToolData):
    parameters = None
    
    def __init__(self):
        self.parameters = {} # for SubDialog
        
        doc = c4d.documents.GetActiveDocument()
        op = doc.GetActiveObject()
        if op and op.IsInstanceOf(c4d.Opolygon):
            self.parameters["OP"] = op
        else:
            self.parameters["OP"] = None
            
        self.parameters["OriginPolygonIndices"] = -1
        self.parameters["SelectedPolygonIndices"] = -1
        self.parameters["LastOriginPolygonIndex"] = -1
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
            polygon = PolygonHelper(op, nbr)            
            originPolygonIndices = []
            
            # 利用 self.parameters 初始化已有的参数
            if op == self.parameters["OP"]:
                originPolygonIndices = self.parameters["OriginPolygonIndices"]
                if not originPolygonIndices:
                    originPolygonIndices = []
            else:
                # ?未解决：切换op时，以当前选择的最后2个为origin（多个选择时，未/无需细分确认最后）
                selectedPolygonIndices = polygon.GetSelectedPolygonIndices()
                if selectedPolygonIndices:
                    if len(selectedPolygonIndices) >= 2:
                        originPolygonIndices.extend(selectedPolygonIndices[-2:])
                    elif len(selectedPolygonIndices) == 1:
                        originPolygonIndices.append(selectedPolygonIndices[0])
            
            if len(originPolygonIndices) != 2:
                print "Please select 2 polygons."
                return True

            # 以下2行很重要，先设置origin才可以计算
            polygon.SetOriginPolygonIndices(originPolygonIndices)
            self.parameters["OriginPolygonIndices"] = polygon.GetOriginPolygonIndices()
            self.parameters["OP"] = op
            
            flag = False
            if (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QCTRL):
                # [Ctrl+up/down] UpPolygons/DownPolygons
                if key == c4d.KEY_UP:
                    print "{0}".format("Ctrl+Up")
                    
                    self.parameters["StepAmount"] += 1
                    
                    stepAmount = 0
                    polygonIndices = None
                    side, stepDistance = polygon.GetUpDownStepDistance()
                    print "side, stepDistance:", side, stepDistance
                    if stepDistance != 0:
                        stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(self.parameters["StepAmount"])
                    
                    if polygonIndices:
                        print "ori:", originPolygonIndices, "side:", StringHelper.SideToString(side), " polygons:", polygonIndices
                        polygon.SetSelectedPolygonIndices(polygonIndices)
                        # 修改为 GetUpDownPolygonIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same side."
                        self.parameters["StepAmount"] -= 1
                        
                    flag = True
                    
                elif key == c4d.KEY_DOWN:
                    print "{0}".format("Ctrl+Down")
                    
                    self.parameters["StepAmount"] -= 1
                    
                    stepAmount = 0
                    polygonIndices = None
                    side, stepDistance = polygon.GetUpDownStepDistance()
                    print "side, stepDistance:", side, stepDistance
                    if stepDistance != 0:
                        stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(self.parameters["StepAmount"])
                    
                    if polygonIndices:
                        print "ori:", originPolygonIndices, "side:", StringHelper.SideToString(side), " polygons:", polygonIndices
                        polygon.SetSelectedPolygonIndices(polygonIndices)
                        # 修改为 GetUpDownPolygonIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same side."
                        self.parameters["StepAmount"] += 1
                        
                    flag = True
                    
                elif key == c4d.KEY_LEFT:
                    print "{0}".format("Ctrl+Left")
                    
                    stepAmount = 0
                    polygonIndices = None
                    side, stepDistance = polygon.GetUpDownStepDistance()
                    if stepDistance != 0:
                        lastStepAmount = 0
                        stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(lastStepAmount + 1)
                        # 
                        while stepAmount != lastStepAmount:
                            lastStepAmount = stepAmount
                            stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(lastStepAmount + 1)
                    
                    if polygonIndices:
                        print "ori:", originPolygonIndices, "side:", StringHelper.SideToString(side), " polygons:", polygonIndices
                        polygon.SetSelectedPolygonIndices(polygonIndices)
                        # 修改为 GetUpDownPolygonIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] = 0
                        
                    flag = True
                    
                elif key == c4d.KEY_RIGHT: # 同c4d.KEY_LEFT
                    print "{0}".format("Ctrl+Right")
                    
                    stepAmount = 0
                    polygonIndices = None
                    side, stepDistance = polygon.GetUpDownStepDistance()
                    if stepDistance != 0:
                        lastStepAmount = 0
                        stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(lastStepAmount + 1)
                        # 
                        while stepAmount != lastStepAmount:
                            lastStepAmount = stepAmount
                            stepAmount, polygonIndices = polygon.GetUpDownPolygonIndicesByStepAmount(lastStepAmount + 1)
                    
                    if polygonIndices:
                        print "ori:", originPolygonIndices, "side:", StringHelper.SideToString(side), " polygons:", polygonIndices
                        polygon.SetSelectedPolygonIndices(polygonIndices)
                        # 修改为 GetUpDownPolygonIndicesByStepAmount 返回的可达到的最大值
                        self.parameters["StepAmount"] = stepAmount
                    else:
                        print "Not same direction."
                        self.parameters["StepAmount"] = 0
                        
                    flag = True
                    
                elif key == ord('L'): # ascii转换
                    print "{0}".format("Ctrl+L --- Loop in other direction")
                    
                    polygonIndices = None
                    side, stepDistance = polygon.GetUpDownStepDistance()
                    print "SD:", stepDistance
                    if stepDistance != 0: # 原方向为UpDown，则other Side = loop
                        polygonIndices = polygon.GetUpDownLoopPolygonIndices(side)
                    
                    if polygonIndices:
                        print "ori:", originPolygonIndices, "Side:", StringHelper.SideToString(side), " polygons:", polygonIndices
                        polygon.SetSelectedPolygonIndices(polygonIndices)
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
        
        # -------- Mouse click: BFM_INPUT_MOUSELEFT 时，+/- polygons
        op = doc.GetActiveObject()
        if op and op.IsInstanceOf(c4d.Opolygon):                
            #利用 self.parameters 初始化已有的参数（不严谨，切换op时其实已经无效）
            if op == self.parameters["OP"]:
                pass
            else:
                self.parameters["LastOriginPolygonIndex"] = -1

            nbr = c4d.utils.Neighbor()
            nbr.Init(op)
            polygon = PolygonHelper(op, nbr)
            originPolygonIndices = []
            
            # 切换op时，以当前选择的最后2个为origin（多个选择时，未/无需细分确认最后）
            selectedPolygonIndices = polygon.GetSelectedPolygonIndices()
            if selectedPolygonIndices:
                if len(selectedPolygonIndices) >= 2:
                    originPolygonIndices.extend(selectedPolygonIndices[-2:])
                elif len(selectedPolygonIndices) == 1:
                    originPolygonIndices.append(selectedPolygonIndices[0])


            polygonIndex = polygon.GetPolygonIndexUnderMouse(doc, bd, sx, sy)
            if polygonIndex != -1:
                originIndex = ArrayHelper.GetIndex(originPolygonIndices, polygonIndex)
                # Ctrl/Shift+click 切换，如果超过两个，则只保留最后选的那个和新选的
                if (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QCTRL) or (msg[c4d.BFM_INPUT_QUALIFIER] & c4d.QSHIFT):
                    if originIndex != -1: # 当前已作为origin，则从origin中删除
                        del originPolygonIndices[originIndex]
                        
                        if len(originPolygonIndices) != 0: # 删除当前之后，可能无已选择
                            self.parameters["LastOriginPolygonIndex"] = originPolygonIndices[0]
                        else:
                            self.parameters["LastOriginPolygonIndex"] = -1
                    else: # 加新，去旧（只保留最后选的那个）
                        originIndex2 = ArrayHelper.GetIndex(originPolygonIndices, self.parameters["LastOriginPolygonIndex"])
                        if originIndex2 != -1 and len(originPolygonIndices) == 2: # 当前已作为origin，则从origin2中删除不是最后的那个
                            if originIndex2 == 0:
                                del originPolygonIndices[1]
                            elif originIndex2 == 1:
                                del originPolygonIndices[0]
                                
                        elif originIndex2 == -1 and len(originPolygonIndices) == 2: # 无法判断时，删除[0]
                            del originPolygonIndices[0]
                        
                        originPolygonIndices.append(polygonIndex)
                        self.parameters["LastOriginPolygonIndex"] = polygonIndex
                else: # 单纯click，只选择当前
                    originPolygonIndices = [polygonIndex]
                    self.parameters["LastOriginPolygonIndex"] = polygonIndex
                
                # 设置origin & selected
                polygon.SetOriginPolygonIndices(originPolygonIndices)
                originIndices = polygon.GetOriginPolygonIndices()
                #print "originIndices:", originIndices
                polygon.SetSelectedPolygonIndices(originPolygonIndices)                         
                    
                # 保存参数
                self.parameters["OP"] = op
                self.parameters["OriginPolygonIndices"] = polygon.GetOriginPolygonIndices()
                self.parameters["StepAmount"] = 0 # 每次选择完 origin，则重新计算 stepAmount
                
                c4d.DrawViews(c4d.DA_ONLY_ACTIVE_VIEW|c4d.DA_NO_THREAD|c4d.DA_NO_ANIMATION) # 界面更新
                
            nbr.Flush()
            
        return True
         
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
                polygon = None
                    
                nbr = c4d.utils.Neighbor()
                nbr.Init(op)
                polygon = PolygonHelper(op, nbr)
                    
                polygonIndex = polygon.GetPolygonIndexUnderMouse(doc, bd, x, y)
                if polygonIndex != -1:
                    polygon.SetPolygonIndex(polygonIndex)
                    #print "polygon:", polygon
                    
                    # ======= 画高亮线 ========
                    bh = c4d.plugins.BaseDrawHelp(bd, doc)
                    if bh and doc.GetMode() == c4d.Mpolygons: # polygonmode
                        #bd.SetMatrix_Matrix(op, bh.GetMg()) # 坐标切换无效?
                        bd.SetPointSize(100) # 高亮线粗细
                        bd.SetPen(c4d.GetViewColor(c4d.VIEWCOLOR_SELECTION_PREVIEW))
                        #bd.SetPen(c4d.GetViewColor(c4d.VIEWCOLOR_ACTIVEPOINT))
                        
                        ppos = polygon.GetPointsPosition() # local
                        apos, bpos, cpos, dpos = ppos[0] * op.GetMg(), ppos[1] * op.GetMg(), ppos[2] * op.GetMg(), ppos[3] * op.GetMg() # local转换成global
                        ##DrawPolygon无效?
                        #p = ( apos, bpos, cpos, dpos )
                        #f = ( c4d.Vector(1,1,1), c4d.Vector(1,1,1), c4d.Vector(1,1,1), c4d.Vector(1,1,1))
                        #bd.DrawPolygon(p, f)
                        
                        apos2D, bpos2D, cpos2D, dpos2D = bd.WS(apos), bd.WS(bpos), bd.WS(cpos), bd.WS(dpos)
                        bd.DrawLine2D(apos2D, bpos2D) # 使用DrawLine2D可以（只有边界有效?）
                        bd.DrawLine2D(bpos2D, cpos2D)
                        bd.DrawLine2D(cpos2D, dpos2D)
                        bd.DrawLine2D(dpos2D, apos2D)
                        
                        c4d.DrawViews(c4d.DA_ONLY_ACTIVE_VIEW|c4d.DA_NO_THREAD|c4d.DA_NO_ANIMATION) # 界面更新
                    # ======= end: 画高亮线 ========
                
                nbr.Flush()
                
        bc.SetString(c4d.RESULT_BUBBLEHELP, plugins.GeLoadString(IDS_SIMPLELOOPSELECTIONPOLYGON_TOOLTIP))
        #bc.SetLong(c4d.RESULT_CURSOR, c4d.MOUSE_POINT_HAND) # 设置鼠标样式
        return False

    # 每次都生成一个新实例，并参数同步（引用）
    def AllocSubDialog(self, bc):
        #return SimpleLoopSelectionPolygonDialog()
        return SimpleLoopSelectionPolygonDialog(self.parameters)


if __name__ == "__main__":
    bmp = bitmaps.BaseBitmap()
    dir, file = os.path.split(__file__)
    fn = os.path.join(dir, "res", "tsimpleloopselectionpolygon.tif")
    bmp.InitWith(fn)
    plugins.RegisterToolPlugin(id=PLUGIN_ID, str="Simple Loop Selection Polygon",
                                info=0, icon=bmp, 
                                help="Simple Loop Selection Polygon help",
                                dat=SimpleLoopSelectionPolygon())

                                
                                