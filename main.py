"""
The final script that will call everything in /src to do the following 

1. Get the intro of wikipedia pages of all the companies that are listed on the S&P 500
2. Use an LLM with an engineered prompt to transform the original text into text that is better suited for vectorization
3. Vectorize each company's sanitized profile text using an embedding model
4. Cluster the vectors using a machine learning algorithm (HDBSCAN) 
5. Create a visualization of the clusters
6. (OPTIONAL) Feed clustering results back into an LLM to label each cluster with a human readable name



"""