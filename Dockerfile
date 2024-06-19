FROM python:slim

# https://github.com/include-what-you-use/include-what-you-use/blob/master/README.md#clang-compatibility
ARG IWYU_BRANCH=clang_13
ARG CLANG_VERSION=13

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -q -y && \
    apt-get install -y --no-install-recommends software-properties-common && \
    apt-get update -q -y && \
    apt-get install -y --no-install-recommends wget curl git make cmake gcc g++ \
        libncurses-dev zlib1g-dev \
        python3 python-is-python3 && \
    apt-get clean


# clang
RUN wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh && chmod +x /tmp/llvm.sh
RUN /tmp/llvm.sh "${CLANG_VERSION}" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/llvm.sh
RUN apt-get update -q -y && \
    apt-get install -y --no-install-recommends llvm-${CLANG_VERSION}-dev libclang-${CLANG_VERSION}-dev clang-${CLANG_VERSION} && \
    update-alternatives --install /usr/bin/clang   clang   "/usr/bin/clang-${CLANG_VERSION}" 999 \
        --slave   /usr/bin/clang++ clang++ "/usr/bin/clang++-${CLANG_VERSION}" && \
    apt-get clean

# Include-what-you-use
RUN mkdir /target && \
    mkdir iwyu && mkdir iwyu/build && \
    git clone -b "${IWYU_BRANCH}" https://github.com/include-what-you-use/include-what-you-use.git iwyu/include-what-you-use
WORKDIR /iwyu/build
RUN cmake -G "Unix Makefiles" \
        "-DCMAKE_PREFIX_PATH=/usr/lib/llvm-${CLANG_VERSION}" \
        "-DIWYU_LLVM_ROOT_PATH=/usr/lib/llvm-${CLANG_VERSION}" \
        ../include-what-you-use && \
    make && make install && \
    ln -s "$(command -v include-what-you-use)" /usr/local/bin/iwyu

# Make the compiler built-in includes accessible to iwyu
RUN mkdir /usr/local/lib/clang && \
    ln -s /usr/lib/clang/* /usr/local/lib/clang/

# copy imp
COPY imp/ /opt/iwyu/


VOLUME [ "/target" ]
WORKDIR /target

ENTRYPOINT [ "include-what-you-use" ]
CMD [ "--version" ]
