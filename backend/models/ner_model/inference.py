from __future__ import absolute_import, division, print_function, unicode_literals
import json
import pickle
import argparse
import torch
import os
from pathlib import Path
from kobert.pytorch_kobert import get_pytorch_kobert_model
from kobert.utils import get_tokenizer
from model.net import KobertSequenceFeatureExtractor, KobertCRF, KobertBiLSTMCRF, KobertBiGRUCRF
from gluonnlp.data import SentencepieceTokenizer
from data_utils.utils import Config
from data_utils.vocab_tokenizer import Tokenizer
from data_utils.pad_sequence import keras_pad_fn

# 전역 모델 캐시
_ner_model = None
_tokenizer = None
_decoder = None
_index_to_ner = None
_device = None

def main(parser):

    args = parser.parse_args()
    model_dir = Path(args.model_dir)
    model_config = Config(json_path=model_dir / 'config.json')

    # Vocab & Tokenizer
    # tok_path = get_tokenizer() # ./tokenizer_78b3253a26.model
    tok_path = "./ptr_lm_model/tokenizer_78b3253a26.model"
    ptr_tokenizer = SentencepieceTokenizer(tok_path)

    # load vocab & tokenizer
    with open(model_dir / "vocab.pkl", 'rb') as f:
        vocab = pickle.load(f)

    tokenizer = Tokenizer(vocab=vocab, split_fn=ptr_tokenizer, pad_fn=keras_pad_fn, maxlen=model_config.maxlen)

    # load ner_to_index.json
    with open(model_dir / "ner_to_index.json", 'rb') as f:
        ner_to_index = json.load(f)
        index_to_ner = {v: k for k, v in ner_to_index.items()}

    # Model
    # model = KobertSequenceFeatureExtractor(config=model_config, num_classes=len(ner_to_index))
    model = KobertCRF(config=model_config, num_classes=len(ner_to_index), vocab=vocab)
    # model = KobertBiLSTMCRF(config=model_config, num_classes=len(ner_to_index), vocab=vocab)
    # model = KobertBiGRUCRF(config=model_config, num_classes=len(ner_to_index), vocab=vocab)

    # load
    model_dict = model.state_dict()
    # checkpoint = torch.load("./experiments/base_model/best-epoch-9-step-600-acc-0.845.bin", map_location=torch.device('cpu'))

    # checkpoint = torch.load("./experiments/base_model_with_crf/best-epoch-16-step-1500-acc-0.993.bin", map_location=torch.device('cpu'))
    checkpoint = torch.load("./experiments/base_model_with_crf_val/best-epoch-12-step-1000-acc-0.960.bin", map_location=torch.device('cpu'))
    # checkpoint = torch.load("./experiments/base_model_with_bilstm_crf/best-epoch-15-step-2750-acc-0.992.bin", map_location=torch.device('cpu'))
    # checkpoint = torch.load("./experiments/base_model_with_bigru_crf/model-epoch-18-step-3250-acc-0.997.bin", map_location=torch.device('cpu'))

    convert_keys = {}
    for k, v in checkpoint['model_state_dict'].items():
        new_key_name = k.replace("module.", '')
        if new_key_name not in model_dict:
            print("{} is not int model_dict".format(new_key_name))
            continue
        convert_keys[new_key_name] = v

    model.load_state_dict(convert_keys)
    model.eval()
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

    # n_gpu = torch.cuda.device_count()
    # if n_gpu > 1:
    #     model = torch.nn.DataParallel(model)
    model.to(device)

    decoder_from_res = DecoderFromNamedEntitySequence(tokenizer=tokenizer, index_to_ner=index_to_ner)

    while(True):
        input_text = input("문장을 입력하세요: ")
        list_of_input_ids = tokenizer.list_of_string_to_list_of_cls_sep_token_ids([input_text])
        x_input = torch.tensor(list_of_input_ids).long()

        ## for bert alone
        # y_pred = model(x_input)
        # list_of_pred_ids = y_pred.max(dim=-1)[1].tolist()

        ## for bert crf
        list_of_pred_ids = model(x_input)

        ## for bert bilstm crf & bert bigru crf
        # list_of_pred_ids = model(x_input, using_pack_sequence=False)

        list_of_ner_word, decoding_ner_sentence = decoder_from_res(list_of_input_ids=list_of_input_ids, list_of_pred_ids=list_of_pred_ids)
        print("list_of_ner_word:", list_of_ner_word)
        print("decoding_ner_sentence:", decoding_ner_sentence)


class DecoderFromNamedEntitySequence():
    """NER 태그 시퀀스를 엔티티 리스트로 디코딩하는 클래스"""
    def __init__(self, tokenizer, index_to_ner):
        self.tokenizer = tokenizer
        self.index_to_ner = index_to_ner

    def __call__(self, list_of_input_ids, list_of_pred_ids):
        input_token = self.tokenizer.decode_token_ids(list_of_input_ids)[0]
        pred_ner_tag = [self.index_to_ner[pred_id] for pred_id in list_of_pred_ids[0]]

        # ----------------------------- parsing list_of_ner_word ----------------------------- #
        list_of_ner_word = []
        entity_word, entity_tag, prev_entity_tag = "", "", ""
        for i, pred_ner_tag_str in enumerate(pred_ner_tag):
            if "B-" in pred_ner_tag_str:
                entity_tag = pred_ner_tag_str[-3:]

                if prev_entity_tag != entity_tag and prev_entity_tag != "":
                    list_of_ner_word.append({"word": entity_word.replace("▁", " "), "tag": prev_entity_tag, "prob": None})

                entity_word = input_token[i]
                prev_entity_tag = entity_tag
            elif "I-"+entity_tag in pred_ner_tag_str:
                entity_word += input_token[i]
            else:
                if entity_word != "" and entity_tag != "":
                    list_of_ner_word.append({"word":entity_word.replace("▁", " "), "tag":entity_tag, "prob":None})
                entity_word, entity_tag, prev_entity_tag = "", "", ""


        # ----------------------------- parsing decoding_ner_sentence ----------------------------- #
        decoding_ner_sentence = ""
        is_prev_entity = False
        prev_entity_tag = ""
        is_there_B_before_I = False

        for token_str, pred_ner_tag_str in zip(input_token, pred_ner_tag):
            token_str = token_str.replace('▁', ' ')  # '▁' 토큰을 띄어쓰기로 교체

            if 'B-' in pred_ner_tag_str:
                if is_prev_entity is True:
                    decoding_ner_sentence += ':' + prev_entity_tag+ '>'

                if token_str[0] == ' ':
                    token_str = list(token_str)
                    token_str[0] = ' <'
                    token_str = ''.join(token_str)
                    decoding_ner_sentence += token_str
                else:
                    decoding_ner_sentence += '<' + token_str
                is_prev_entity = True
                prev_entity_tag = pred_ner_tag_str[-3:] # 첫번째 예측을 기준으로 하겠음
                is_there_B_before_I = True

            elif 'I-' in pred_ner_tag_str:
                decoding_ner_sentence += token_str

                if is_there_B_before_I is True: # I가 나오기전에 B가 있어야하도록 체크
                    is_prev_entity = True
            else:
                if is_prev_entity is True:
                    decoding_ner_sentence += ':' + prev_entity_tag+ '>' + token_str
                    is_prev_entity = False
                    is_there_B_before_I = False
                else:
                    decoding_ner_sentence += token_str

        return list_of_ner_word, decoding_ner_sentence


def load_ner_model(model_dir=None, checkpoint_path=None, tokenizer_path=None):
    """
    NER 모델을 로드합니다 (전역 캐시 사용).
    
    Args:
        model_dir: 모델 디렉토리 경로 (기본값: ./experiments/base_model_with_crf_val)
        checkpoint_path: 체크포인트 파일 경로 (기본값: model_dir 내에서 자동 탐색)
        tokenizer_path: 토크나이저 파일 경로 (기본값: ./ptr_lm_model/tokenizer_78b3253a26.model)
    
    Returns:
        (model, tokenizer, decoder, index_to_ner, device) 튜플
    """
    global _ner_model, _tokenizer, _decoder, _index_to_ner, _device
    
    # 이미 로드된 경우 캐시 반환
    if _ner_model is not None:
        return _ner_model, _tokenizer, _decoder, _index_to_ner, _device
    
    # 기본 경로 설정
    if model_dir is None:
        model_dir = Path("./experiments/base_model_with_crf_val")
    else:
        model_dir = Path(model_dir)
    
    if tokenizer_path is None:
        tokenizer_path = "./ptr_lm_model/tokenizer_78b3253a26.model"
    
    # 모델 설정 로드
    model_config = Config(json_path=model_dir / 'config.json')
    
    # 토크나이저 로드
    ptr_tokenizer = SentencepieceTokenizer(tokenizer_path)
    
    # Vocab 로드
    with open(model_dir / "vocab.pkl", 'rb') as f:
        vocab = pickle.load(f)
    
    tokenizer = Tokenizer(vocab=vocab, split_fn=ptr_tokenizer, pad_fn=keras_pad_fn, maxlen=model_config.maxlen)
    
    # NER 인덱스 로드
    with open(model_dir / "ner_to_index.json", 'rb') as f:
        ner_to_index = json.load(f)
        index_to_ner = {v: k for k, v in ner_to_index.items()}
    
    # 모델 생성
    model = KobertCRF(config=model_config, num_classes=len(ner_to_index), vocab=vocab)
    
    # 체크포인트 로드
    if checkpoint_path is None:
        checkpoint_path = model_dir / "best-epoch-12-step-1000-acc-0.960.bin"
        # 체크포인트 파일이 없으면 다른 후보들 시도
        if not checkpoint_path.exists():
            candidates = [
                model_dir / "best-epoch-16-step-1500-acc-0.993.bin",
                model_dir / "best-epoch-9-step-600-acc-0.845.bin",
            ]
            for candidate in candidates:
                if candidate.exists():
                    checkpoint_path = candidate
                    break
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # 모델 가중치 로드
    model_dict = model.state_dict()
    convert_keys = {}
    for k, v in checkpoint['model_state_dict'].items():
        new_key_name = k.replace("module.", '')
        if new_key_name in model_dict:
            convert_keys[new_key_name] = v
    
    model.load_state_dict(convert_keys)
    model.eval()
    model.to(device)
    
    # 디코더 생성
    decoder = DecoderFromNamedEntitySequence(tokenizer=tokenizer, index_to_ner=index_to_ner)
    
    # 전역 캐시에 저장
    _ner_model = model
    _tokenizer = tokenizer
    _decoder = decoder
    _index_to_ner = index_to_ner
    _device = device
    
    return model, tokenizer, decoder, index_to_ner, device


def predict_ner(text, model=None, tokenizer=None, decoder=None, device=None):
    """
    텍스트에서 NER 태그를 예측합니다.
    
    Args:
        text: 입력 텍스트
        model: NER 모델 (None이면 전역 캐시 사용)
        tokenizer: 토크나이저 (None이면 전역 캐시 사용)
        decoder: 디코더 (None이면 전역 캐시 사용)
        device: 디바이스 (None이면 전역 캐시 사용)
    
    Returns:
        list_of_ner_word: 엔티티 리스트 [{"word": "...", "tag": "...", "prob": None}, ...]
    """
    global _ner_model, _tokenizer, _decoder, _device
    
    # 모델이 로드되지 않은 경우 자동 로드
    if _ner_model is None:
        load_ner_model()
    
    # 전역 캐시 사용
    if model is None:
        model = _ner_model
    if tokenizer is None:
        tokenizer = _tokenizer
    if decoder is None:
        decoder = _decoder
    if device is None:
        device = _device
    
    # 토큰화
    list_of_input_ids = tokenizer.list_of_string_to_list_of_cls_sep_token_ids([text])
    x_input = torch.tensor(list_of_input_ids).long().to(device)
    
    # 예측
    with torch.no_grad():
        list_of_pred_ids = model(x_input)
    
    # 디코딩
    list_of_ner_word, _ = decoder(list_of_input_ids=list_of_input_ids, list_of_pred_ids=list_of_pred_ids)
    
    return list_of_ner_word


def extract_per_entities(text):
    """
    텍스트에서 PER(Person) 엔티티만 추출합니다.
    
    Args:
        text: 입력 텍스트
    
    Returns:
        names: 사람 이름 리스트
    """
    list_of_ner_word = predict_ner(text)
    
    # PER 태그만 필터링 (B-PER, I-PER도 포함하되, Decoder에서 이미 "PER"로 변환됨)
    per_names = []
    for entity in list_of_ner_word:
        tag = entity.get("tag", "")
        # PER 태그 또는 B-PER, I-PER 형식 모두 처리
        if tag == "PER" or tag.endswith("-PER") or tag.startswith("PER"):
            # 공백 정리 및 중복 제거
            name = entity.get("word", "").strip()
            # 빈 문자열이나 특수 문자만 있는 경우 제외
            if name and len(name) > 0 and name not in per_names:
                per_names.append(name)
    
    return per_names


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', default='./data_in', help="Directory containing config.json of data")
    # parser.add_argument('--model_dir', default='./experiments/base_model', help="Directory containing config.json of model")
    parser.add_argument('--model_dir', default='./experiments/base_model_with_crf_val', help="Directory containing config.json of model")
    # parser.add_argument('--model_dir', default='./experiments/base_model_with_crf', help="Directory containing config.json of model")
    # parser.add_argument('--model_dir', default='./experiments/base_model_with_bilstm_crf', help="Directory containing config.json of model")
    # parser.add_argument('--model_dir', default='./experiments/base_model_with_bigru_crf', help="Directory containing config.json of model")

    main(parser)