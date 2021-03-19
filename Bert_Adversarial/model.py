import torch
import torch.nn as nn
from pytorch_pretrained_bert import BertModel, BertTokenizer


class FGM():
    def __init__(self, model):
        self.model = model
        self.backup = {}

    def attack(self, epsilon=1., emb_name='bert.embedding'):
        # emb_name这个参数要换成你模型中embedding的参数名
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                self.backup[name] = param.data.clone()
                norm = torch.norm(param.grad)
                if norm != 0:
                    r_at = epsilon * param.grad / norm
                    param.data.add_(r_at)

    def restore(self, emb_name='bert.embedding'):
        # emb_name这个参数要换成你模型中embedding的参数名
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                assert name in self.backup
                param.data = self.backup[name]
        self.backup = {}


class Bert_model(nn.Module):
    def __init__(self, args):
        super(Bert_model, self).__init__()
        self.bert = BertModel.from_pretrained(args.bert_path)
        for param in self.parameters():
            param.requires_grad = True
        self.lstm = nn.LSTM(args.bert_embedding, args.rnn_hidden, args.num_layers,
                            bidirectional=True, batch_first=True, dropout=args.dropout)
        self.dropout = nn.Dropout(args.dropout)
        self.fc_rnn = nn.Linear(args.rnn_hidden * 2, args.num_classes)

    def forward(self, inputs):
        contents = inputs[0]
        segments = inputs[1]
        masks = inputs[2]

        contents = torch.squeeze(contents, dim=1)
        segments = torch.squeeze(segments, dim=1)
        masks = torch.squeeze(masks, dim=1)

        encoder_out, text_cls = self.bert(input_ids=contents, token_type_ids=segments,
                                          attention_mask=masks, output_all_encoded_layers=False)
        out, _ = self.lstm(encoder_out)
        out = self.dropout(out)
        logits = self.fc_rnn(out[:, -1, :])
        probs = nn.functional.softmax(logits, dim=1)
        return logits, probs
