# Hierarchical Graph Autoencoders

This repository contains an implementation of a hierarchical graph autoencoder for molecular representation learning in PyTorch and Deep Graph Library. I have written a detailed tutorial and explanation on the architecture and design decisions which can be found here: [https://noncomputable.github.io/molecules](https://noncomputable.github.io/molecules)

The model and preprocessing pipeline are quite complex and many aspects of the implementation are non-obvious, so I have annotated the code with detailed explanations for various modeling and implementation decisions. The high-level structure is as follows:
* **core** - Contains all models, scripts, and utilities
	* *dataset.py* - Defines a DGL Dataset for sets of molecules 
	* *postprocess.py* - Defines functions for processing model outputs as RDKit molecules
	* *preprocess.py* - Defines functions for processing raw data into DGL hierarchical graphs
	* *train.py* - Defines functions for training and validating the models
	* **models** - Contains model definitions and utils
		* *autoencoder.py* - Defines the high-level structure of a variational autoencoder for hierarchical graphs
		* *decoder.py* - Defines a model that maps embeddings to hierarchical graphs
		* *encoder.py* - Defines a model that maps hierarchical graphs to embeddings
		* *message_passing.py* - Defines graph message-passing operations and models used throughout the autoencoder
		* *predictors.py* - Defines models for predicting node types and attachments between nodes
		* *utils.py* - Defines functions commonly used across models (i.e. for merging and instantiating new hierarchical graphs)
* **data** - Contains both raw and processed molecule data used throughout the pipeline
	* **zinc** - Molecule data extracted from the ZINC compound database
		* **raw** - Contains lists of SMILES strings samples from ZINC
			* *mols.txt* - Contains a list of SMILES strings to be processed and used for training, testing, and validation
		* **processed** - Contains outputs of preprocessing
* *notebook.ipynb* - Annotated notebook illustrating how to do dataset construction, training, and testing with this project
