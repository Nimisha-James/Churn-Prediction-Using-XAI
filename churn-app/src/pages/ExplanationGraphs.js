import React from 'react';

const ExplanationGraphs = ({ shapPlot, limePlot }) => {
  return (
    <div className="graphs-container">
      {shapPlot && (
        <div>
          <h4>SHAP Summary Plot</h4>
          <img
            src={`data:image/png;base64,${shapPlot}`}
            alt="SHAP Plot"
            style={{ maxWidth: '100%' }}
          />
        </div>
      )}

      {limePlot && (
        <div>
          <h4>LIME Explanation</h4>
          <img
            src={`data:image/png;base64,${limePlot}`}
            alt="LIME Plot"
            style={{ maxWidth: '100%' }}
          />
        </div>
      )}
    </div>
  );
};

export default ExplanationGraphs;
