// AI Processor Logic Simulator

window.CropAI = {
  predict: function(soil, water, land) {
    return new Promise((resolve, reject) => {
      // Logic Validation Added
      if (!soil || !water || !land) {
        return reject("validation_error");
      }
      
      setTimeout(() => {
        let crops = [];
        if (soil === 'black') {
           crops.push({ crop: 'Tomato', score: 9.6, match: 'Excellent', before: '₹28,000', after: '₹61,000', reason: 'High demand in Pune · ideal for black soil.'});
           crops.push({ crop: 'Onion', score: 7.2, match: 'Good', before: '₹26,000', after: '₹41,000', reason: 'Stable prices but higher competition.'});
        } else if (soil === 'red') {
           crops.push({ crop: 'Brinjal', score: 8.8, match: 'Excellent', before: '₹22,000', after: '₹48,000', reason: 'Thrives in red laterite · export demand rising.'});
           crops.push({ crop: 'Potato', score: 6.5, match: 'Medium', before: '₹18,000', after: '₹31,000', reason: 'Average yield expected.'});
        } else {
           crops.push({ crop: 'Potato', score: 9.1, match: 'Excellent', before: '₹24,000', after: '₹52,000', reason: 'Best yield in alluvial soil · cold storage near.'});
           crops.push({ crop: 'Wheat', score: 7.8, match: 'Good', before: '₹19,000', after: '₹35,000', reason: 'Consistent local demand.'});
        }

        // Adjust based on water availability
        if (water === 'low') {
           crops.forEach(c => c.score -= 1.5);
           crops.push({ crop: 'Millet (Bajra)', score: 9.5, match: 'Excellent', before: '₹15,000', after: '₹38,000', reason: 'Highly drought resistant.'});
        }

        // Sort by score
        crops.sort((a,b) => b.score - a.score);
        resolve(crops);
      }, 500); // Simulate processing time
    });
  }
};
