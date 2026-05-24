# Let's sort several cubic metres of LEGO (fast)

## Plan : 
- List of the sets into brickset with part list and other infos 
      - (API https://brickset.com/api/v3.asmx)
- Use bricklink instead ? https://www.bricklink.com/v2/api/welcome.page
- Identification of the bricks to be sorted into their respective sets 
      - (API https://api.brickognize.com/docs)

- Basically, an interface between 2 APIs to ease the sorting of several cubic meters of LEGO (relatively quickly)
- User will just have to put the bricks below a webcam and then put the bricks into the correct box in order to reconstitute the sets 
- Edge cases: false positives, wrong identification and a brick belonging to multiple sets ? 
- Checklist of bricks already present in each set ? (excessive maybe)

## TODO 
- [x] get webcam feed and do stuff to each image 
- [/] Setup brickognize and test if it's reliable enough
- [ ] Setup brickset matching to results 
- [ ] set identification from input database
- [ ] Build the set database
- [ ] Sort the 2 cubic metres of plastic bricks