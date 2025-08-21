import { useEffect, useState } from 'react'
import request from './utils/api_utils'
import { ToolCard } from './components/card'
import './App.css'
function App() {
  const [tools, setTools] = useState([]);
  const useCardsPerRow = () => {
    const getCardsPerRow = (width) => {
      const minCardWidth = 350; 
      const cards = Math.floor(width / minCardWidth);
      return cards < 1 ? 1 : cards;
    };
    

    const [cardsPerRow, setCardsPerRow] = useState(getCardsPerRow(window.innerWidth));

    useEffect(() => {
      fetchTools();
      function handleResize() {
        setCardsPerRow(getCardsPerRow(window.innerWidth));
      }
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }, []);

    return cardsPerRow;
  };

  const cardsPerRow = useCardsPerRow();

  function fetchTools() {
    request({
      "url": "/gateway_manager/list_tools/",
      "onSuccess": render_tools_layout
    })
  };

  function render_tools_layout(result) {
    setTools(result);
  }
  const colSize = Math.floor(12 / cardsPerRow);

  return (
    <div className="container p-4">
      <div className="row g-4">
        {tools.map((tool, idx) => (
          <div key={idx} className={`col-12 col-md-${colSize}`}>
            <ToolCard name={tool.name} description={tool.description} />
          </div>
        ))}
      </div>
    </div>
  );
}
export default App
