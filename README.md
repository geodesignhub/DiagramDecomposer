# DiagramSplitter
This plugin reads a large diagram (by area) from Geodesignhub and splits it into three subcomponents of 70% area, 20% area and 10% of the area and then uploads them back to Geodesign. 

It can be useful when there is a large diagram that can be too expensive to build or if you want to split diagram into stages. Currently, it decomposes randomly 

## Example 
It is best to illustrate this by example. The image below is the raw source diagram that we want to decompose. It is a large ~ 9 Hectares and we want to decompose it into smaller diagrams. The raw diagram is below firstly on Geodesignhub
![Raw Diagram](https://i.imgur.com/PiUKOjO.png) 

and then as GeoJSON below
![](https://i.imgur.com/srdwnFN.png)

Once the diagram geometry is read by the plugin it splits the diagram into 1 hectare grid. The grid is then split randomly into three components: 
![comb](https://i.imgur.com/3Eh6mQX.png)

70% area: 
![70-area](https://i.imgur.com/5Stbto5.png)
20% area: 
![20-area](https://i.imgur.com/NqcaLw9.png)
10% area: 
![10-area](https://i.imgur.com/eXvunZ6.png)

These three are then uploaded to Geodesignhub as new diagrams.