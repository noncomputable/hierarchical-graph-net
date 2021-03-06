import torch, dgl
from core.models.message_passing import HierMessagePassingNet, RNN_MPN, GCN
from core.models.encoder import Encoder
from core.models.decoder import Decoder

class Autoencoder(torch.nn.Module):
    def __init__(self, vocabs, motif_graphs,
                 node_rep_size, latent_size, rep_activation, neighbor_hops,
                 attach_prediction_method = "dot",
                 dropout = 0.0, variational = False, device = "cpu",
                 mpn_model = RNN_MPN, **mpn_kwargs):
        """
        Args:
        vocabs - Dict of vocabs generated by preprocessing.
        motif_graphs - List[i] = hgraph containing only atoms of ith motif in vocab.
        node_rep_size - Size of embeddings for nodes.
        rep_activation - Activation function the MPN uses.
        neighbor_hops - Num times to run MPN (so info propagates this distance from nodes).
        attach_prediction_method - How to predict the prob of a pair of atoms attaching:
           "dot": pass the dot product of atom reps through MLP.
           "concat": pass the concatenation of atom reps through MLP.
        dropout - Dropout to use in MLPs and LSTM.
        variational - Whether it's predicting latent vectors directly or mean/var vectors.
        device -
        mpn_model - The message passing model to use at each level of the hgraph.
        mpn_kwargs - Kwargs to initialize each hgraph level's mpn.
        """
        super().__init__()
        
        levels = [("atom", "bond", "atom"),
                  ("attachment_config", "attaches to", "attachment_config"),
                  ("motif", "attaches to", "motif")]
        if len(vocabs) != len(levels):
            raise ValueError("There must be as many vocabs as there are levels.")
       
        embed_size = node_rep_size
        hidden_size = 0 if "hidden_size" not in mpn_kwargs else mpn_kwargs["hidden_size"]
        embeddors = torch.nn.ModuleDict({
            "nodes": torch.nn.ModuleDict({}),
            "edges": torch.nn.ModuleDict({})
        })
        for (node_type, _, _) in levels:
            embeddors["nodes"][node_type] = torch.nn.Embedding(len(vocabs[node_type]["node"]), embed_size)
            embeddors["edges"][node_type] = torch.nn.Embedding(len(vocabs[node_type]["edge"]), embed_size)
        embeddors["nodes"]["position"] = torch.nn.Embedding(vocabs["motif"]["max_num_atoms"], embed_size)
        
        self.variational = variational
        if variational:
            mean_encoder_mpn = HierMessagePassingNet(
                node_rep_size, rep_activation, neighbor_hops, dropout,
                mpn_model, **mpn_kwargs
            )
            self.mean_encoder = Encoder(hidden_size, node_rep_size, latent_size,
                                        dropout, embeddors, mean_encoder_mpn, device)
            
            log_var_encoder_mpn = HierMessagePassingNet(
                node_rep_size, rep_activation, neighbor_hops, dropout,
                mpn_model, **mpn_kwargs
            )
            self.log_var_encoder = Encoder(hidden_size, node_rep_size, latent_size,
                                           dropout, embeddors, log_var_encoder_mpn, device)
        else:
            encoder_mpn = HierMessagePassingNet(
                node_rep_size, rep_activation, neighbor_hops, dropout,
                mpn_model, **mpn_kwargs
            )
            self.encoder = Encoder(hidden_size, node_rep_size, latent_size,
                                   dropout, embeddors, encoder_mpn, device)
        
        decoder_mpn = HierMessagePassingNet(
            node_rep_size, rep_activation, neighbor_hops, dropout,
            mpn_model, **mpn_kwargs
        )
        self.decoder = Decoder(
            vocabs, motif_graphs, hidden_size, node_rep_size, latent_size,
            attach_prediction_method, dropout, embeddors, decoder_mpn, device
        )
        
        self.device = device
        self.to(device)

    def forward(self, hgraphs, target_graphs = None, max_motifs = 1e9,
                deterministic = True):
        """
        Args:
        hgraphs - A list of DGL hierarchical graphs.
        target_graphs - For training: list of graphs to decode hgraphs into.
        max_motifs - Maximum number of motifs to add to a generated hgraph.
        deterministic - Whether to generate latents variationally or deterministically.
        """

        if not self.variational:
            latents = self.encoder(hgraphs)
        else:
            means = self.mean_encoder(hgraphs)
            log_vars = self.log_var_encoder(hgraphs)
            
            if deterministic:
                latents = means
            else:
                noise = torch.randn(means.shape)
                latents = means + noise * torch.exp(log_vars / 2)

        if target_graphs is None:
            outputs = self.decoder(latents, target_graphs, max_motifs)
            return outputs
        else:
            outputs, reconst_loss = self.decoder(latents, target_graphs, max_motifs)
            
            if self.variational:
                kl_loss = (
                    0.5 * torch.sum(torch.exp(log_vars) + means**2 - 1. - log_vars)
                )
            else:
                kl_loss = torch.tensor(0)

            return outputs, reconst_loss, kl_loss
