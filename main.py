import os
import sys
import argparse
import subprocess
from rvc.configs.config import Config
from rvc.lib.tools.validators import (
    validate_sampling_rate,
    validate_f0up_key,
    validate_f0method,
    validate_true_false,
)

from rvc.train.extract.preparing_files import generate_config, generate_filelist
from rvc.lib.tools.pretrained_selector import pretrained_selector

config = Config()
logs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs")
subprocess.run(["python", "rvc/lib/tools/prerequisites_download.py"])


# Infer
def run_infer_script(f0up_key, f0method, input_path, output_path, pth_file, index_path):
    command = [
        "python",
        "rvc/infer/infer.py",
        str(f0up_key),
        f0method,
        input_path,
        output_path,
        pth_file,
        index_path,
    ]
    subprocess.run(command)


# Preprocess
def run_preprocess_script(model_name, dataset_path, sampling_rate):
    per = 3.0 if config.is_half else 3.7
    command = [
        "python",
        "rvc/train/preprocess/preprocess.py",
        os.path.join(logs_path, str(model_name)),
        dataset_path,
        str(sampling_rate),
        str(per),
    ]

    os.mkdir(os.path.join(logs_path, str(model_name)))
    subprocess.run(command)


# Extract
def run_extract_script(
    model_name, rvc_version, f0method, crepe_hop_length, sampling_rate
):
    model_path = os.path.join(logs_path, str(model_name))
    command_1 = [
        "python",
        "rvc/train/extract/extract_f0_print.py",
        model_path,
        f0method,
        crepe_hop_length,
    ]
    command_2 = [
        "python",
        "rvc/train/extract/extract_feature_print.py",
        config.device,
        "1",
        "0",
        "0",
        model_path,
        rvc_version,
        "True",
    ]
    subprocess.run(command_1)
    subprocess.run(command_2)

    generate_config(rvc_version, sampling_rate, model_path)
    generate_filelist(f0method, model_path, rvc_version, sampling_rate)


# Train
def run_train_script(
    model_name,
    rvc_version,
    save_every_epoch,
    total_epoch,
    sampling_rate,
    batch_size,
    pretrained,
    pitch_guidance,
):
    f0 = 1 if pitch_guidance == "True" else 0

    if pretrained == "True":
        pg, pd = pretrained_selector(f0)[rvc_version][sampling_rate]
    else:
        pg, pd = "", ""

    command = [
        "python",
        "rvc/train/train.py",
        "-se",
        str(save_every_epoch),
        "-te",
        str(total_epoch),
        "-pg",
        pg,
        "-pd",
        pd,
        "-sr",
        str(sampling_rate),
        "-bs",
        str(batch_size),
        "-e",
        os.path.join(logs_path, str(model_name)),
        "-v",
        rvc_version,
        "-l",
        "0",
        "-c",
        "0",
        "-sw",
        "0",
        "-f0",
        str(f0),
    ]

    subprocess.run(command)


# Index
def run_index_script(model_name, rvc_version):
    command = [
        "python",
        "rvc/train/index_generator.py",
        os.path.join(logs_path, str(model_name)),
        rvc_version,
    ]

    subprocess.run(command)


# Model information
def run_model_information_script(pth_path):
    command = [
        "python",
        "rvc/lib/tools/model_information.py",
        pth_path,
    ]
    subprocess.run(command)


# Tensorboard
def run_tensorboard_script():
    command = [
        "python",
        "rvc/lib/tools/launch_tensorboard.py",
    ]
    subprocess.run(command)


# Download
def run_download_script(model_link):
    command = [
        "python",
        "rvc/lib/tools/model_download.py",
        model_link,
    ]
    subprocess.run(command)


# Parse arguments
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run the main.py script with specific parameters."
    )
    subparsers = parser.add_subparsers(
        title="subcommands", dest="mode", help="Choose a mode"
    )

    # Parser for 'infer' mode
    infer_parser = subparsers.add_parser("infer", help="Run inference")
    infer_parser.add_argument(
        "f0up_key", type=validate_f0up_key, help="Value for f0up_key (-12 to +12)"
    )
    infer_parser.add_argument(
        "f0method",
        type=validate_f0method,
        help="Value for f0method (pm, dio, crepe, crepe-tiny, mangio-crepe, mangio-crepe-tiny, harvest, rmvpe)",
    )
    infer_parser.add_argument(
        "input_path", type=str, help="Input path (enclose in double quotes)"
    )
    infer_parser.add_argument(
        "output_path", type=str, help="Output path (enclose in double quotes)"
    )
    infer_parser.add_argument(
        "pth_file", type=str, help="Path to the .pth file (enclose in double quotes)"
    )
    infer_parser.add_argument(
        "index_path",
        type=str,
        help="Path to the .index file (enclose in double quotes)",
    )

    # Parser for 'preprocess' mode
    preprocess_parser = subparsers.add_parser("preprocess", help="Run preprocessing")
    preprocess_parser.add_argument(
        "model_name", type=str, help="Name of the model (enclose in double quotes)"
    )
    preprocess_parser.add_argument(
        "dataset_path",
        type=str,
        help="Path to the dataset (enclose in double quotes)",
    )
    preprocess_parser.add_argument(
        "sampling_rate",
        type=validate_sampling_rate,
        help="Sampling rate (32000, 40000 or 48000)",
    )

    # Parser for 'extract' mode
    extract_parser = subparsers.add_parser("extract", help="Run extract")
    extract_parser.add_argument(
        "model_name",
        type=str,
        help="Name of the model (enclose in double quotes)",
    )
    extract_parser.add_argument(
        "rvc_version",
        type=str,
        help="Version of the model (v1 or v2)",
    )
    extract_parser.add_argument(
        "f0method",
        type=validate_f0method,
        help="Value for f0method (pm, dio, crepe, crepe-tiny, mangio-crepe, mangio-crepe-tiny, harvest, rmvpe)",
    )
    extract_parser.add_argument(
        "crepe_hop_length", type=str, help="Value for crepe_hop_length (1 to 512)"
    )
    extract_parser.add_argument(
        "sampling_rate",
        type=validate_sampling_rate,
        help="Sampling rate (32000, 40000 or 48000)",
    )
    # Parser for 'train' mode
    train_parser = subparsers.add_parser("train", help="Run training")
    train_parser.add_argument(
        "model_name",
        type=str,
        help="Name of the model (enclose in double quotes)",
    )
    train_parser.add_argument(
        "rvc_version",
        type=str,
        help="Version of the model (v1 or v2)",
    )
    train_parser.add_argument(
        "save_every_epoch",
        type=str,
        help="Save every epoch",
    )
    train_parser.add_argument(
        "total_epoch",
        type=str,
        help="Total epoch",
    )
    train_parser.add_argument(
        "sampling_rate",
        type=validate_sampling_rate,
        help="Sampling rate (32000, 40000 or 48000)",
    )
    train_parser.add_argument(
        "batch_size",
        type=str,
        help="Batch size",
    )
    train_parser.add_argument(
        "pretrained",
        type=validate_true_false,
        help="Pretrained (True or False)",
    )
    train_parser.add_argument(
        "pitch_guidance",
        type=validate_true_false,
        help="Pitch guidance (True or False)",
    )

    # Parser for 'index' mode
    index_parser = subparsers.add_parser("index", help="Generate index file")
    index_parser.add_argument(
        "model_name",
        type=str,
        help="Name of the model (enclose in double quotes)",
    )
    index_parser.add_argument(
        "rvc_version",
        type=str,
        help="Version of the model (v1 or v2)",
    )

    # Parser for 'model_information' mode
    model_information_parser = subparsers.add_parser(
        "model_information", help="Print model information"
    )
    model_information_parser.add_argument(
        "pth_path",
        type=str,
        help="Path to the .pth file (enclose in double quotes)",
    )

    # Parser for 'tensorboard' mode
    subparsers.add_parser("tensorboard", help="Run tensorboard")

    # Parser for 'download' mode
    download_parser = subparsers.add_parser("download", help="Download models")
    download_parser.add_argument(
        "model_link",
        type=str,
        help="Link of the model (enclose in double quotes)",
    )

    return parser.parse_args()


def main():
    if len(sys.argv) == 1:
        print("Please run the script with '-h' for more information.")
        sys.exit(1)

    args = parse_arguments()

    try:
        if args.mode == "infer":
            run_infer_script(
                args.f0up_key,
                args.f0method,
                args.input_path,
                args.output_path,
                args.pth_file,
                args.index_path,
            )
        elif args.mode == "preprocess":
            run_preprocess_script(
                args.model_name,
                args.dataset_path,
                str(args.sampling_rate),
            )

        elif args.mode == "extract":
            run_extract_script(
                args.model_name,
                args.rvc_version,
                args.f0method,
                args.crepe_hop_length,
                args.sampling_rate,
            )
        elif args.mode == "train":
            run_train_script(
                args.model_name,
                args.rvc_version,
                args.save_every_epoch,
                args.total_epoch,
                args.sampling_rate,
                args.batch_size,
                args.pretrained,
                args.pitch_guidance,
            )
        elif args.mode == "index":
            run_index_script(
                args.model_name,
                args.rvc_version,
            )
        elif args.mode == "model_information":
            run_model_information_script(
                args.pth_path,
            )
        elif args.mode == "tensorboard":
            run_tensorboard_script()
        elif args.mode == "download":
            run_download_script(
                args.model_link,
            )
    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
