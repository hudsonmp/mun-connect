import pymc3 as pm

class BayesianStyleProfiler:
    def __init__(self, style_dimensions):
        self.dimensions = style_dimensions
        # Initialize with neutral priors
        self.beliefs = {dim: {'mean': 0.5, 'variance': 0.25} for dim in self.dimensions}
        
    def update_beliefs(self, bert_features_a, bert_features_b, chosen):
        """Update beliefs based on comparison and choice"""
        mapper = StyleDimensionMapper(self.dimensions)
        
        # Map BERT features to style dimensions
        style_a = mapper.map_features(bert_features_a)
        style_b = mapper.map_features(bert_features_b)
        
        # Update each dimension with Bayesian inference
        updated_beliefs = {}
        
        for dim in self.dimensions:
            # Current belief
            prior_mean = self.beliefs[dim]['mean']
            prior_var = self.beliefs[dim]['variance']
            
            # Observed signal (difference between styles)
            signal = style_a[dim] - style_b[dim]
            if chosen == 'B':  # If user chose option B
                signal = -signal  # Reverse the signal
                
            # Perform Bayesian update using PyMC3
            with pm.Model() as model:
                # Prior distribution
                theta = pm.Normal('theta', mu=prior_mean, sigma=np.sqrt(prior_var))
                
                # Likelihood function - how likely is this observation given the belief
                # We use a normal distribution with fixed observation noise
                obs_var = 0.1  # Fixed observation noise
                likelihood = pm.Normal('y', mu=theta, sigma=np.sqrt(obs_var), observed=signal)
                
                # Sample from the posterior
                trace = pm.sample(1000, progressbar=False, chains=1)
                
                # Extract posterior statistics
                posterior_mean = float(pm.summary(trace)['mean']['theta'])
                posterior_var = float(pm.summary(trace)['sd']['theta'])**2
                
            # Store updated belief
            updated_beliefs[dim] = {
                'mean': posterior_mean,
                'variance': posterior_var
            }
            
        # Replace old beliefs with updated ones
        self.beliefs = updated_beliefs
        return self.beliefs