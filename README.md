# SimpleLoopSelection
Loop/step select edges/polygons based on the first 2 edges/polygons in c4d

The idea comes from the plugin named "Devert Advanced Loop Selection". It implements all the funcitons that Devert's has, and fix the follow problems that Devert's has:

1)When select 2 edges/polygons around X axis on a polygon such as sphere(made editable), the 2 edges/polygons would be recognized as in 2 different directions, even if the 2 are in the same line.
    
2)When select 2 edges/polygons and press Ctrl+L to make a loop selection on a polygon such as sphere(made editable),the triangle edges/polygons are included in the result selection, which is not correct.
