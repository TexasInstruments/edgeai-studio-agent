
import './App.css';
import React, {useState, useEffect } from 'react';

function App() {
 
  // we will return the HTML. Since status is a bool
  // we need to + '' to convert it into a string

  const [Loop, setLoop] = useState(false);
  var newImage = new Image();
  newImage.src = "http://10.201.1.115:8080/stream/";
  var count = 0;
  function updateImage()
  {
      if(newImage.complete) {
          document.getElementById("theText").src = newImage.src;
          newImage = new Image();
          newImage.src = "http://10.201.1.115:8080/stream/" + count++ + ".jpg";
      }
      setTimeout(updateImage, 0);
  }


/*useEffect(()=>{
  
  // setInterval(()=>{
    Loop && updateImage()
  // },1000)
},[Loop])*/
const toggleState =()=>{
  setLoop(!Loop)
}
  return (
    <div className="App">
     <img id ='theText' src = "http://10.201.1.115:8080/stream"/>
     
      <button onClick={toggleState}>Toggle</button>
     
    </div>
  );


}


export default App;
